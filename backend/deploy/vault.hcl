ui = false
api_addr = "https://vault:8200"
disable_mlock = false

listener "tcp" {
  address         = "0.0.0.0:8200"
  tls_min_version = "tls12"
  tls_cert_file   = "/vault/tls/vault.pem"
  tls_key_file    = "/vault/tls/vault-key.pem"
}

storage "file" {
  path = "/vault/file"
}
