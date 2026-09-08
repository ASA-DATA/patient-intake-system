# Backend migrations and Azure deployment

This document describes the one-time Azure setup required by
`.github/workflows/deploy-backend.yml`. Run provisioning commands only from an
authorized administrative session. The GitHub Actions workflow validates this
configuration but does not create identities, role assignments, secrets, or the
migration job.

## Required deployment resources

The production resources are:

- Resource group: `patient-intake-system-rg`
- Backend Container App: `patient-intake-api`
- Migration Container Apps Job: `patient-intake-migrate`
- ACR login server: `patientintakeacr2026.azurecr.io`
- Backend image repository: `patient-intake-backend`

The migration job must be in the same Container Apps Environment as the backend.
It uses one manual execution replica, parallelism `1`, completion count `1`, a
30-minute replica timeout, and an explicit retry limit of `0`. A failed migration
therefore requires investigation and an intentional retry; it never triggers an
automatic database downgrade.

## One-time provisioning

The following Bash example is reproducible but intentionally contains
placeholders. `DATABASE_URL` must already exist as a Key Vault secret. Never copy
its value into a shell command, GitHub secret, workflow file, or Container Apps
plain-text environment variable.

```bash
set -euo pipefail

az extension add --name containerapp --upgrade

RESOURCE_GROUP="patient-intake-system-rg"
CONTAINER_APP="patient-intake-api"
MIGRATION_JOB="patient-intake-migrate"
MIGRATION_IDENTITY="patient-intake-migrate-identity"
ACR_NAME="patientintakeacr2026"
ACR_LOGIN_SERVER="patientintakeacr2026.azurecr.io"
DATABASE_KEY_VAULT="<key-vault-name>"
DATABASE_SECRET_NAME="<database-url-secret-name>"

environment_id="$(az containerapp show \
  --name "$CONTAINER_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.environmentId \
  --output tsv)"
backend_image="$(az containerapp show \
  --name "$CONTAINER_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --query 'properties.template.containers[0].image' \
  --output tsv)"

if [[ -z "$backend_image" || "$backend_image" == *":latest" ]]; then
  echo "Choose an existing immutable backend SHA tag or digest before provisioning the job."
  exit 1
fi

az identity create \
  --name "$MIGRATION_IDENTITY" \
  --resource-group "$RESOURCE_GROUP" \
  --output none

identity_id="$(az identity show \
  --name "$MIGRATION_IDENTITY" \
  --resource-group "$RESOURCE_GROUP" \
  --query id \
  --output tsv)"
identity_principal_id="$(az identity show \
  --name "$MIGRATION_IDENTITY" \
  --resource-group "$RESOURCE_GROUP" \
  --query principalId \
  --output tsv)"
acr_id="$(az acr show --name "$ACR_NAME" --query id --output tsv)"
key_vault_id="$(az keyvault show \
  --name "$DATABASE_KEY_VAULT" \
  --query id \
  --output tsv)"
database_secret_uri="https://${DATABASE_KEY_VAULT}.vault.azure.net/secrets/${DATABASE_SECRET_NAME}"

# Use AcrPull only when the registry uses the RBAC-only permissions mode.
az role assignment create \
  --assignee-object-id "$identity_principal_id" \
  --assignee-principal-type ServicePrincipal \
  --role AcrPull \
  --scope "$acr_id"

az role assignment create \
  --assignee-object-id "$identity_principal_id" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope "$key_vault_id"

az containerapp job create \
  --name "$MIGRATION_JOB" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$environment_id" \
  --trigger-type Manual \
  --replica-timeout 1800 \
  --replica-retry-limit 0 \
  --replica-completion-count 1 \
  --parallelism 1 \
  --image "$backend_image" \
  --container-name migration \
  --cpu 0.25 \
  --memory 0.5Gi \
  --mi-user-assigned "$identity_id" \
  --registry-server "$ACR_LOGIN_SERVER" \
  --registry-identity "$identity_id" \
  --secrets "database-url=keyvaultref:${database_secret_uri},identityref:${identity_id}" \
  --env-vars "DATABASE_URL=secretref:database-url" \
  --command /bin/sh \
  --args "-c" "alembic upgrade head && alembic current --check-heads" \
  --output none
```

If the registry is configured for **RBAC Registry + ABAC Repository
Permissions**, replace `AcrPull` with `Container Registry Repository Reader`.
Add `Container Registry Repository Catalog Lister` only if the operational tools
also need to enumerate the registry catalog; pulling the configured image does
not require catalog enumeration.

The Key Vault must use the Azure RBAC authorization model, and the referenced
secret must contain the complete SQLAlchemy connection URL. The job definition
stores only a Key Vault reference named `database-url`; its container receives
`DATABASE_URL=secretref:database-url` at runtime.

## GitHub Actions identity and repository configuration

Configure GitHub's Azure login with workload identity federation (OIDC) and the
repository secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and
`AZURE_SUBSCRIPTION_ID`. These values identify the federated principal; no Azure
client secret is needed.

Grant the GitHub Actions principal only the permissions used by the workflow:

- `AcrPush` on the registry when it uses RBAC-only permissions, or `Container
  Registry Repository Writer` on an ABAC-enabled registry. An ABAC condition can
  restrict access to `patient-intake-backend`.
- `Container Apps Jobs Contributor` scoped to `patient-intake-migrate`, because
  the workflow reads and updates the job, starts executions, and reads their
  status.
- `Contributor` scoped to `patient-intake-api`, because the workflow creates a
  new app revision and reads revision and traffic state. A custom role containing
  only the required `Microsoft.App/containerApps` read/write, revision read, and
  traffic actions is preferable where available.

The migration job's user-assigned identity needs:

- `AcrPull` on an RBAC-only registry, or `Container Registry Repository Reader`
  on an ABAC-enabled registry.
- `Key Vault Secrets User` on the database secret or its vault.

If PostgreSQL itself uses Microsoft Entra authentication, grant the job identity
the corresponding database permissions separately. That is independent of the
Container Apps and Key Vault roles above.

## Safe configuration checks

These commands display configuration metadata only. They do not print the value
of `DATABASE_URL` and do not start a migration.

```bash
az containerapp job show \
  --name patient-intake-migrate \
  --resource-group patient-intake-system-rg \
  --query '{environment:properties.environmentId,trigger:properties.configuration.triggerType,timeout:properties.configuration.replicaTimeout,retries:properties.configuration.replicaRetryLimit,manual:properties.configuration.manualTriggerConfig,identityType:identity.type,container:properties.template.containers[0].{name:name,image:image,command:command,args:args,databaseSecretRef:env[?name==`DATABASE_URL`].secretRef|[0]}}' \
  --output yaml

az containerapp job execution list \
  --name patient-intake-migrate \
  --resource-group patient-intake-system-rg \
  --query '[].{name:name,status:properties.status,startTime:properties.startTime,endTime:properties.endTime}' \
  --output table

latest_revision="$(az containerapp show \
  --name patient-intake-api \
  --resource-group patient-intake-system-rg \
  --query properties.latestRevisionName \
  --output tsv)"

az containerapp revision show \
  --name patient-intake-api \
  --resource-group patient-intake-system-rg \
  --revision "$latest_revision" \
  --query '{revision:name,provisioningState:properties.provisioningState,image:properties.template.containers[0].image}' \
  --output yaml

az containerapp show \
  --name patient-intake-api \
  --resource-group patient-intake-system-rg \
  --query 'properties.configuration.ingress.traffic' \
  --output table

fqdn="$(az containerapp show \
  --name patient-intake-api \
  --resource-group patient-intake-system-rg \
  --query properties.configuration.ingress.fqdn \
  --output tsv)"

curl --fail --silent --show-error "https://${fqdn}/health"
curl --fail --silent --show-error "https://${fqdn}/ready"
```

Expected metadata is: trigger `Manual`, timeout `1800`, retry limit `0`,
parallelism `1`, completion count `1`, container name `migration`, and a
`DATABASE_URL` secret reference named `database-url`. A completed migration
execution must be `Succeeded`. The deployed revision must be `Provisioned`, use
the current immutable SHA image, receive 100% traffic under this deployment
policy, and return HTTP 200 from both HTTP checks.

Starting `patient-intake-migrate` is intentionally absent from the safe checks:
`az containerapp job start` performs a real production migration. Run it only
through the reviewed production workflow or an authorized recovery procedure.

After deployment, `/health` must return HTTP 200 as a lightweight liveness
check. `/ready` must return HTTP 200 only when PostgreSQL is reachable and every
database revision in `alembic_version` exactly matches the Alembic head shipped
in the application image.

## Migration compatibility: expand and contract

Production migrations run before the new application revision. At that moment,
the previous revision still serves requests, so every migration must remain
compatible with both revisions:

1. **Expand:** add nullable columns, new tables, indexes, or parallel structures
   without removing or changing behavior required by the old revision.
2. Deploy application code that works with both the old and expanded schema.
3. Backfill data separately when required and verify that old revisions no
   longer receive traffic.
4. **Contract:** remove obsolete columns, constraints, or structures only in a
   later deployment.

Never use an automatic `alembic downgrade` as a deployment rollback. If the new
application fails verification, retain the migrated schema, inspect the failed
revision, and intentionally restore traffic to the previous compatible revision
or redeploy its immutable image.

The migration `8f4c2a1d9b7e_add_assessment_date_index.py` is expand-compatible:
it only creates a non-unique index and does not change table data or the contract
used by the previous application. Its downgrade only removes that index. The
current `op.create_index` uses PostgreSQL's regular `CREATE INDEX`, which can
block writes to `intake_submissions` while the index is built. Assess table size
and migration duration before the first production run. Do not edit this
migration if it has already been applied; if online index creation becomes
necessary, handle it in a reviewed follow-up migration and deployment plan.

## References

- [Jobs in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/jobs)
- [Azure Container Apps job CLI](https://learn.microsoft.com/cli/azure/containerapp/job)
- [Managed identity image pulls](https://learn.microsoft.com/azure/container-apps/managed-identity-image-pull)
- [Container Apps secret references](https://learn.microsoft.com/azure/container-apps/manage-secrets)
- [Azure built-in roles](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles)
- [ACR permissions and ABAC](https://learn.microsoft.com/azure/container-registry/container-registry-rbac-abac-repository-permissions)
