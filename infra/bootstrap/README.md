# Azure deployment-identity bootstrap

**Operator-run, one environment, no application deployment.**
This OpenTofu root creates a user-assigned managed identity and the GitHub
configuration a future Azure deployment job will need. It does not create a
cache service, container registry, app host, or CI/CD pipeline.

## Resources and trust

| Resource | Default / boundary |
| --- | --- |
| Azure resource group | `rg-hoard-dev`, newly owned by this state |
| User-assigned managed identity | `id-hoard-dev-github` |
| Federated trust | `repo:Stonefly-Labs/Hoard:environment:dev` |
| Issuer / audience | GitHub Actions / `api://AzureADTokenExchange` |
| Azure role | Contributor **only on that resource group** |
| GitHub environment | `dev`, with an exact `main` branch deployment policy |
| Environment variables | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_LOCATION` |

There is no subscription-wide deployment permission, client secret, GitHub
deployment credential secret, or Entra app registration. Contributor cannot
grant roles; a later feature that needs RBAC assignments requires a separately
reviewed permission decision. Contributor is still broad within this dedicated
group, including its identity: restrict edits to deployment workflows and
review any proposal to separate the identity into an operator-only group.

The repository's normal GitHub environment subject format is assumed. A custom
organization/repository OIDC subject template needs a corresponding explicit IaC
change. Tags cannot use this environment; release and deployment remain separate.

## Prerequisites and permission boundary

- OpenTofu 1.11+, Azure CLI, GitHub CLI, Git.
- An explicit Azure subscription and region chosen by the operator.
- Azure permission to create the dedicated group/identity and assign Contributor
  at that scope (e.g. Contributor plus Role Based Access Control Administrator
  at the parent scope, or a suitable bootstrap operator role).
- `Microsoft.ManagedIdentity` registered in the chosen subscription. Provider
  auto-registration is disabled to avoid unrelated subscription-level changes.
- GitHub access to manage this repository's environments, deployment policies,
  and Actions variables. A fine-grained token needs repository Environments
  read/write and Variables read/write permissions; classic tokens need suitable
  repository access and any organization SSO authorization.

The **human/bootstrap operator** authenticates initially. The future deployment
identity cannot create its own initial role assignment. Do not run this root in
a PR, release workflow, or future application deploy job.

## Validate without touching Azure or GitHub

```bash
tofu -chdir=infra/bootstrap fmt -check
tofu -chdir=infra/bootstrap init -backend=false
tofu -chdir=infra/bootstrap validate
tofu -chdir=infra/bootstrap test
```

Tests use **mock providers**, including mocked apply operations. They do not
authenticate, create resources, change GitHub settings, or need real tfvars.
Initialization downloads providers; commit `.terraform.lock.hcl`, never
`.terraform/`.

## Plan and apply (only with explicit authorization)

From the repository root:

```bash
az login
az account set --subscription YOUR_SUBSCRIPTION_ID
az account show --query '{subscription:id, tenant:tenantId}' -o table
gh auth status

cp infra/bootstrap/bootstrap.tfvars.example infra/bootstrap/bootstrap.tfvars
# Edit bootstrap.tfvars: replace the subscription UUID and region.
# Confirm exact GitHub owner/repository case and environment name.

export GITHUB_TOKEN="$(gh auth token)"
tofu -chdir=infra/bootstrap init
tofu -chdir=infra/bootstrap plan -var-file=bootstrap.tfvars -out=bootstrap.tfplan
tofu -chdir=infra/bootstrap show bootstrap.tfplan
# Verify account, scope, permissions, environment, and main-only policy.
tofu -chdir=infra/bootstrap apply bootstrap.tfplan
unset GITHUB_TOKEN
```

Never paste tokens into tfvars, logs, issues, or commits. The Azure provider uses
your Azure CLI session and the explicitly supplied subscription. The GitHub
provider reads `GITHUB_TOKEN` from the process environment, not from state inputs.
Do not reuse the all-zero/example subscription value or region placeholder.

**Existing resources:** stop if `rg-hoard-dev` or `dev` already exists under
another owner/state. Review/import the exact resources rather than overwriting
environment protections or adopting a production group accidentally. This root
does not manage repository branch protection, required reviews, or rulesets.

## Verify after an authorized apply

```bash
tofu -chdir=infra/bootstrap output
gh api repos/Stonefly-Labs/Hoard/environments/dev
gh variable list --repo Stonefly-Labs/Hoard --env dev
az identity federated-credential list \
  --resource-group rg-hoard-dev --identity-name id-hoard-dev-github
az role assignment list --assignee \
  "$(az identity show -g rg-hoard-dev -n id-hoard-dev-github --query principalId -o tsv)" \
  --scope "$(az group show -n rg-hoard-dev --query id -o tsv)" -o table
```

Allow for Azure role/federation propagation. An identity login smoke test belongs
in the first explicitly authorized deployment workflow; it is not silently
installed by this bootstrap.

## How a future deployment job will consume it

The future job must run from `main`, select `environment: dev`, and declare
`permissions: {contents: read, id-token: write}`. With a SHA-pinned
[`azure/login`](https://github.com/Azure/login) action, pass:

```yaml
with:
  client-id: ${{ vars.AZURE_CLIENT_ID }}
  tenant-id: ${{ vars.AZURE_TENANT_ID }}
  subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
```

Those identifiers are **environment variables (`vars`)**, not secrets. GitHub's
short-lived OIDC token is the credential. The release job does not select the
environment and has no `id-token: write` permission.

## State, recovery, and teardown

This small operator root uses **local state by default**. No remote storage
account is created. Run from one controlled checkout/operator at a time; local
state is not safe for concurrent operators. Keep state and its backups outside
Git in access-controlled, encrypted storage. Treat state and saved plans as
sensitive even though this root does not generate a client secret. Losing state
requires careful imports; do not delete it and reapply.

Before multi-operator use, agree on an Azure Blob backend, encryption/access,
locking, and recovery policy, then migrate with `tofu init -migrate-state`.
That storage and migration are deliberately outside this bootstrap.

After failure, preserve state, inspect the error/actual resources, and rerun plan
with the same inputs. A partial GitHub/Azure apply can be reconciled; do not mask
provider errors or create manual duplicate credentials.

Destruction revokes trust/roles, removes the environment/variables, and attempts
to delete the owned group/identity. **Do not destroy a group later used by an
application**. The provider refuses group deletion while unrelated resources
remain. Only an explicitly authorized operator should review a destroy plan
and its impact before applying it.
