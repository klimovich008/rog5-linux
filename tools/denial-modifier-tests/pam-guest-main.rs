// Offline guest entry for the unmodified Denial PAM backend extracted by the builder.
// No supplied password, host authentication, display, logind or lock UI is exercised.
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cmdline = std::fs::read_to_string("/proc/cmdline")?;
    if !cmdline.split_whitespace().any(|v| v == "rog5.pam_fixture=1")
        || !std::path::Path::new("/sys/bus/virtio/devices").is_dir()
        || std::fs::read_to_string("/run/pam-fixture")? != "synthetic accounts only\n"
    {
        return Err("not the isolated PAM guest fixture".into());
    }
    // SAFETY: these libc identity queries take no pointers or mutate process state.
    if unsafe { libc::getuid() } != 1000 || unsafe { libc::geteuid() } != 1000 {
        return Err("PAM fixture must start as UID1000".into());
    }
    if std::fs::File::open("/etc/shadow").is_ok() {
        return Err("unprivileged fixture can read shadow".into());
    }
    let args: Vec<_> = std::env::args().skip(1).collect();
    let [kind] = args.as_slice() else { return Err("expected valid or wrong".into()); };
    let password: &[u8] = match kind.as_str() {
        // Public synthetic fixtures, never installed or used for a real account.
        "valid" => b"rog5-public-pam-fixture",
        "wrong" => b"rog5-wrong-pam-fixture",
        _ => return Err("expected valid or wrong".into()),
    };
    let mut backend = PamBackend::load()?;
    let mut prompts = 0;
    let mut conversation = |style, _message: &str| {
        match style {
            PromptStyle::EchoOff if prompts == 0 => {
                prompts += 1;
                Some(SecureString::new(password))
            }
            PromptStyle::EchoOn => Some(SecureString::new(b"mobile")),
            PromptStyle::Info | PromptStyle::Error => Some(SecureString::new(b"")),
            _ => None,
        }
    };
    let result = backend.authenticate("mobile", &mut conversation, &|| false);
    println!("PAM_BACKEND result={result:?} secret_prompts={prompts}");
    if prompts != 1 { return Err("expected exactly one secret prompt".into()); }
    Ok(())
}
