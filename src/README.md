# Backend boundaries (reserved)

These directories reserve the assembly boundaries from
[the architecture](../docs/ARCHITECTURE.md). They contain no .NET projects or
implementation. The relevant specifications introduce build/toolchain manifests
and project references—not this bootstrap.

| Directory | Future responsibility |
| --- | --- |
| `Hoard.Abstractions` | Minimal stable provider contracts |
| `Hoard.Core` | Shared cache correctness and orchestration |
| `Hoard.Hosting` | Module registration, validation, lifecycle |
| `Hoard.Application` | Management vertical slices |
| `Hoard.Host` | Curated executable composition |
| `Hoard.Protocols.NuGet` | First protocol adapter and its slices |
| `Hoard.Persistence.Sqlite` | First metadata provider, private schema |
| `Hoard.Storage.FileSystem` | First artifact provider |
| `Hoard.Identity.Local` | Reserved local identity-provider boundary |

Do not infer public signatures, packages, or runnable features from the
directory names. Project naming/API decisions are finalized in feature plans.
