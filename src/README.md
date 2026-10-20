# Backend boundaries

These directories reserve the assembly boundaries from
[the architecture](../docs/ARCHITECTURE.md). F-01 introduces four packable .NET 10
libraries at local acceptance version `0.1.0`; none is published. See the
[provider guide](../docs/PROVIDERS.md) for ownership and compatibility.

| Directory | Current scope / reserved responsibility |
| --- | --- |
| `Hoard.Abstractions` | BCL-only immutable declarations and four provider family markers |
| `Hoard.Core` | Empty provider-free library; references Abstractions only, no engine yet |
| `Hoard.Hosting` | DI declaration/type records only; no activation, selection, validation, HTTP, or lifecycle |
| `Hoard.Application` | Empty library referencing Core/Abstractions; no management slices yet |
| `Hoard.Host` | Reserved curated executable composition |
| `Hoard.Protocols.NuGet` | Reserved first protocol adapter and its slices |
| `Hoard.Persistence.Sqlite` | Reserved metadata provider, private schema |
| `Hoard.Storage.FileSystem` | Reserved artifact provider |
| `Hoard.Identity.Local` | Reserved local identity-provider boundary |

Build with `dotnet restore Hoard.slnx --locked-mode` followed by
`dotnet build Hoard.slnx --configuration Release --no-restore`.
Run `bash scripts/validate-foundation.sh` for isolated package/Core/host and
architecture/compatibility acceptance. There is no runnable cache or provider.
Shared correctness and operational contracts remain later feature work, not
empty placeholder methods added to these libraries.
