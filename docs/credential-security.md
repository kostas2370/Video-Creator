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

1. Stage the new release and verify Vault availability. Stop the old API and scheduler,
   drain and stop both workers, and take a fresh database backup. Keep the previous
   release and configuration for restoration.
2. Export the exact old Fernet key into a private file. If the old deployment derived it
   from Django's signing secret, reproduce the old URL-safe base64 encoding of the
   SHA-256 digest using the original signing secret. Mount the file read-only in the
   one-off migration container. Keep it outside the runtime containers and checkout.
3. Run the new release's `python manage.py migrate --noinput` while the app is offline.
   The credential columns remain text, and this schema step preserves their contents.
4. Run the conversion from the staged backend directory. With the local Vault overlay,
   define the Compose command and mount the old key only for the first two calls:

   ```sh
   compose() { docker compose -f docker-compose.beta.yml -f docker-compose.vault.yml "$@"; }
   legacy_key_path=/absolute/private/path/to/old-key
   compose run --rm --no-deps -T --volume "$legacy_key_path:/run/secrets/viddie-legacy-key:ro" video_creator python manage.py migrate_credentials --legacy-key-file /run/secrets/viddie-legacy-key
   compose run --rm --no-deps -T --volume "$legacy_key_path:/run/secrets/viddie-legacy-key:ro" video_creator python manage.py migrate_credentials --legacy-key-file /run/secrets/viddie-legacy-key --apply
   compose run --rm --no-deps -T video_creator python manage.py migrate_credentials --verify
   ```

   The first command checks both ciphers without writing. The second verifies each
   replacement before saving it and can resume after an interruption. The last command
   checks Vault and fails if legacy values remain. If a value cannot be opened with the
   old key, investigate it before cutover. The command does not treat unreadable values
   as plaintext and cannot recover a missing key.
5. Only after verification, start the upgraded API and workers, check credential status
   and a provider or publishing workflow, and remove the old key from live configuration.
   Keep a protected copy of the old key while any required backups contain legacy
   ciphertext. A rollback to the old app needs the matching pre-migration database and
   configuration. Keep Vault storage and keys with the post-migration backups.

The first conversion is a manual maintenance step. For later beta deployments using
the local Vault service, create `/opt/viddie/backend/.use-compose-vault` and install the
updated [deployment helper](../scripts/deploy_beta.py). It includes the Compose overlay
when the marker is present and runs the verification command before restarting Viddie.
