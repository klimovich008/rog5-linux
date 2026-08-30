// SPDX-License-Identifier: GPL-2.0-only
/* QEMU-only availability check; no keys, packets or device accesses. */
#include <crypto/aead.h>
#include <crypto/hash.h>
#include <crypto/skcipher.h>
#include <linux/err.h>
#include <linux/module.h>

static int __init wifi_crypto_probe_init(void)
{
	const char *hashes[] = { "sha256", "cmac(aes)" };
	const char *aeads[] = { "ccm(aes)", "gcm(aes)" };
	struct crypto_skcipher *skcipher;
	struct crypto_shash *hash;
	struct crypto_aead *aead;
	int i;

	for (i = 0; i < ARRAY_SIZE(hashes); i++) {
		hash = crypto_alloc_shash(hashes[i], 0, CRYPTO_ALG_ASYNC);
		if (IS_ERR(hash)) {
			pr_err("ROG5_WIFI_CRYPTO_FAIL %s %ld\n", hashes[i], PTR_ERR(hash));
			return PTR_ERR(hash);
		}
		crypto_free_shash(hash);
		pr_info("ROG5_WIFI_CRYPTO_PASS %s\n", hashes[i]);
	}
	for (i = 0; i < ARRAY_SIZE(aeads); i++) {
		aead = crypto_alloc_aead(aeads[i], 0, CRYPTO_ALG_ASYNC);
		if (IS_ERR(aead)) {
			pr_err("ROG5_WIFI_CRYPTO_FAIL %s %ld\n", aeads[i], PTR_ERR(aead));
			return PTR_ERR(aead);
		}
		crypto_free_aead(aead);
		pr_info("ROG5_WIFI_CRYPTO_PASS %s\n", aeads[i]);
	}
	skcipher = crypto_alloc_skcipher("ctr(aes)", 0, CRYPTO_ALG_ASYNC);
	if (IS_ERR(skcipher)) {
		pr_err("ROG5_WIFI_CRYPTO_FAIL ctr(aes) %ld\n", PTR_ERR(skcipher));
		return PTR_ERR(skcipher);
	}
	crypto_free_skcipher(skcipher);
	pr_info("ROG5_WIFI_CRYPTO_PASS ctr(aes)\n");
	return 0;
}

static void __exit wifi_crypto_probe_exit(void) { }
module_init(wifi_crypto_probe_init);
module_exit(wifi_crypto_probe_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("QEMU-only Wi-Fi crypto transform availability test");
