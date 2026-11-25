# Credential security and Vault rollout

Viddie stores provider API keys, custom provider secrets and publishing tokens as
Vault Transit ciphertext. Account passwords use Django's password hashing. Viddie's
credential admin shows only the owner and timestamps to superusers. The owner-scoped
APIs continue to mask secrets.

The [Vault Transit API](https://developer.hashicorp.com/vault/api-docs/secret/transit)
keeps the encryption key inside Vault. Enable Vault audit logging and restrict Viddie's
token to the supplied [Transit policy](../backend/deploy/vault-viddie-policy.hcl).
Viddie still receives plaintext when its API or workers need to call a provider.
Full compromise of one of those processes can expose credentials reachable through
its Vault token. Preventing that requires moving credential use and authorization to a
separate provider service that never returns plaintext.

## Run Vault as a Docker service

Use `backend/docker-compose.vault.yml` alongside either Viddie Compose file. A
single-node Vault runs on a private Docker network with no published port and a
persistent `credential-vault-data` volume. The API and workers share access to that
network. To isolate Vault from compromise of the VPS itself, run it on a separate
host and configure Viddie with its private HTTPS endpoint and mounted token and CA
files.

For Compose on the VPS, set these values in the private backend `.env`:

- `VIDDIE_VAULT_IMAGE` is a supported HashiCorp Vault image pinned to a version or digest.
- `VIDDIE_VAULT_TLS_DIR` is an absolute host directory containing `ca.pem`,
  `vault.pem` and `vault-key.pem`. The server certificate must have the
  `vault` DNS subject alternative name. Limit access to the server key.
- `VIDDIE_VAULT_TOKEN_PATH` is an absolute host path to a private file for the short
  lived application token. Keep this file outside the release checkout and ensure the
  Django container user can read it.

From the backend directory start only Vault. Use `docker-compose.yml` in place of
`docker-compose.beta.yml` for local development.

```sh
docker compose -f docker-compose.beta.yml -f docker-compose.vault.yml up -d vault
```

[Initialize and unseal Vault](https://developer.hashicorp.com/vault/docs/commands/operator/init)
under an operator account. Store recovery material separately and enable a persistent
[audit device](https://developer.hashicorp.com/vault/docs/audit).
With an authenticated Vault CLI, create the Transit key and install the policy:

```sh
vault secrets enable transit
vault write transit/keys/viddie-credentials type=aes256-gcm96 derived=true exportable=false
vault policy write viddie-credentials deploy/vault-viddie-policy.hcl
```

Issue the application token under the `viddie-credentials` policy and arrange renewal
or file replacement before it expires. When a bind-mounted secret is replaced by
renaming the host file, recreate the consumers so they see the new inode. Back up Vault
storage, keep the unseal material outside the VPS, and test Vault recovery together
with a database restore. Vault needs to be unsealed after a restart unless you set up
auto-unseal.

## Upgrade an existing deployment

1. Set up Vault and confirm the new release can use it. With the Compose service,
   create `/opt/viddie/backend/.use-compose-vault` and install the updated
   [deployment helper](../scripts/deploy_beta.py). It includes the Compose overlay and
   runs the Vault check before stopping the old application.
2. Take a database backup. Before deploying, manually remove stored provider keys
   and connection tokens that are not Vault ciphertext. Do this during maintenance
   so the running application cannot recreate incompatible entries. Deploy the new
   release. The normal deployment runs Django's schema migrations. It does not
   convert or clear stored credentials.
   Vault is the only credential cipher accepted by the running application.
3. Sign in as the user with stored provider credentials and save fresh keys in
   the usual settings. Any publishing accounts with old tokens need to reconnect.
   Account records, provider settings, and publishing history are preserved.

The running application accepts empty values and Vault ciphertext only. Unsupported
stored values fail closed; there is no format translation or compatibility fallback.
Keep protected configuration/database backups for recovery. Back up Vault storage and
recovery material with the database created after cutover.

## Local verification and operations

Use a separate database and Compose project for disposable probes, or back up your
existing local database before applying the upgrade. Keep operator recovery material,
TLS private keys and database backups outside the source directories mounted into
the application. The ignored `.viddie-local-vault/` directory at the repository root
can hold private local setup files; it must never be committed or copied into an image.

Run `python manage.py check_credential_vault` inside the configured API container to
verify a real TLS encryption/decryption round trip without calling a paid provider.
Check that the provider settings API masks saved keys. The database should contain
`viddie:vault:1:` values, and the app token must not be able to create encryption keys.
Restart Vault and unseal it, then verify that the same saved credential still works.

The supplied policy allows the app token to renew itself. A periodic token can be
renewed by an operator-managed timer before its period ends. Capture or discard the
renewal response: it contains the token and must not appear in logs. Store audit logs
in the dedicated persistent volume. Ordinary application releases leave Vault running;
a VPS or Vault restart requires unsealing unless an external auto-unseal service is
configured. Keep recovery material and a Vault storage backup off the VPS.
