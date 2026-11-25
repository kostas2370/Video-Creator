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
2. Take a database backup and deploy the new release. The normal deployment
   runs Django's schema migrations. Vault is the only credential cipher used
   by the running application, and this upgrade requires no legacy key input.
3. Sign in as the user with stored provider credentials and save fresh keys in
   the usual settings. Any publishing accounts with old tokens need to reconnect.
   Account records, provider settings, and publishing history are preserved.

On the new release, old credential entries appear unset until replaced.
The schema change preserves existing ciphertext, and Viddie never attempts to
decrypt it. Remove the previous encryption key from the live configuration, and
retain a protected copy only if needed to restore an older backup. Back up Vault
storage and recovery material with the database created after cutover.
