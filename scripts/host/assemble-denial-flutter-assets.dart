import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_tools/src/asset.dart';
import 'package:flutter_tools/src/artifacts.dart';
import 'package:flutter_tools/src/build_info.dart';
import 'package:flutter_tools/src/build_system/tools/shader_compiler.dart';
import 'package:flutter_tools/src/cache.dart';
import 'package:flutter_tools/src/context_runner.dart';
import 'package:flutter_tools/src/globals.dart' as globals;
import 'package:standard_message_codec/standard_message_codec.dart';

// Run with the pinned flutter_tools package configuration. Keep the resolved
// application at its package-config path; relocating it changes relative roots.
Future<void> main(List<String> args) async {
  if (args.length != 4) {
    throw ArgumentError('usage: project-root flutter-root engine-output output-directory');
  }
  final projectRoot = args[0];
  final flutterRoot = args[1];
  final engineRoot = args[2];
  final outputRoot = args[3];
  Cache.flutterRoot = flutterRoot;
  await runInContext(() async {
    final fs = globals.fs;
    for (final path in args) {
      if (!fs.path.isAbsolute(path)) throw ArgumentError('absolute paths required');
    }
    fs.currentDirectory = projectRoot;
    final configFile = fs.file('$projectRoot/.dart_tool/package_config.json');
    final config = jsonDecode(configFile.readAsStringSync()) as Map;
    for (final package in config['packages'] as List) {
      final root = configFile.uri.resolve(package['rootUri'] as String);
      if (root.scheme != 'file' || !fs.directory(root.toFilePath()).existsSync()) {
        throw StateError('unresolved package root: ${package['name']}: $root');
      }
    }
    if (fs.directory('$outputRoot/flutter_assets').existsSync()) {
      throw StateError('refusing existing asset output');
    }
    final bundle = ManifestAssetBundle(logger: globals.logger, fileSystem: fs,
        platform: globals.platform, flutterRoot: flutterRoot);
    final status = await bundle.build(manifestPath: '$projectRoot/pubspec.yaml',
        packageConfigPath: configFile.path,
        targetPlatform: TargetPlatform.linux_arm64);
    if (status != 0) throw StateError('asset bundle build failed: $status');
    final root = fs.directory('$outputRoot/flutter_assets')..createSync(recursive: true);
    final shader = ShaderCompiler(processManager: globals.processManager,
        logger: globals.logger, fileSystem: fs,
        artifacts: Artifacts.getLocalEngine(EngineBuildPaths(
            targetEngine: engineRoot, hostEngine: '$engineRoot/clang_x64', webSdk: null)));
    final records = <Map<String, Object?>>[];
    for (final item in bundle.entries.entries) {
      if (item.value.transformers.isNotEmpty) throw StateError('unhandled asset transformer');
      final path = fs.path.normalize(item.key);
      if (fs.path.isAbsolute(path) || path.startsWith('../')) throw StateError('asset path escape');
      final output = root.childFile(path);
      output.parent.createSync(recursive: true);
      if (item.value.kind == AssetKind.shader) {
        final input = fs.file('$outputRoot/shader-inputs/$path');
        input.parent.createSync(recursive: true);
        final sink = input.openWrite();
        await sink.addStream(item.value.content.contentsAsStream());
        await sink.close();
        await shader.compileShader(input: input, outputPath: output.path,
            targetPlatform: TargetPlatform.linux_arm64);
      } else {
        final sink = output.openWrite();
        await sink.addStream(item.value.content.contentsAsStream());
        await sink.close();
      }
      if (!output.existsSync() || output.lengthSync() == 0) throw StateError('empty asset $path');
      records.add({'path': path, 'kind': item.value.kind.name, 'size': output.lengthSync()});
    }
    final manifestBytes = root.childFile('AssetManifest.bin').readAsBytesSync();
    final manifest = const StandardMessageCodec().decodeMessage(ByteData.sublistView(manifestBytes)) as Map;
    var variants = 0;
    for (final value in manifest.values) {
      for (final entry in value as List) {
        final path = (entry as Map)['asset'] as String;
        if (!root.childFile(path).existsSync()) throw StateError('missing manifest variant $path');
        variants++;
      }
    }
    final fonts = jsonDecode(root.childFile('FontManifest.json').readAsStringSync()) as List;
    var fontFiles = 0;
    for (final family in fonts) {
      for (final font in family['fonts'] as List) {
        if (!root.childFile(font['asset'] as String).existsSync()) throw StateError('missing font');
        fontFiles++;
      }
    }
    final result = {'status': 'PASS', 'entries': records, 'manifest_variants': variants,
        'font_files': fontFiles, 'fonts_subset': false,
        'scope': 'real Flutter manifest/font/shader asset assembly; no application or physical startup'};
    fs.file('$outputRoot/asset-result.json').writeAsStringSync('${const JsonEncoder.withIndent('  ').convert(result)}\n');
    print('PASS ${records.length} assets, $variants manifest variants, $fontFiles font files');
  });
}
