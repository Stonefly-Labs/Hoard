using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Fixtures.Metadata.Sqlite;
using static CrashData;

if (args.Length != 4) { throw new ArgumentException("Expected fixed recovery scenario arguments."); }
var mode = args[0];
var database = Path.GetFullPath(args[1]);
var control = Path.GetFullPath(args[2]);
var barrier = args[3];
var json = new JsonSerializerOptions();
string FileAt(string name) => Path.Combine(control, name);
void Write<T>(string name, T value) => File.WriteAllText(FileAt(name), JsonSerializer.Serialize(value, json));
T Load<T>(string name) => JsonSerializer.Deserialize<T>(File.ReadAllText(FileAt(name)), json) ?? throw new InvalidOperationException("Missing private recovery input.");
async ValueTask Hold(string point)
{
    Write("barrier.json", new { barrier = point, pid = Environment.ProcessId });
    await Task.Delay(TimeSpan.FromMinutes(5));
    throw new TimeoutException("Parent did not terminate its recovery child.");
}
string Digest(MetadataReadSnapshot snapshot) => Convert.ToHexStringLower(SHA256.HashData(MetadataEncoding.Encode(snapshot).AsSpan()));
async Task<MetadataFixtureSession> Open(string compatible = "fixture-sqlite-v2", bool create = false)
{
    var result = MetadataFixtureSession.Create("sqlite", new CrashClock(), database, compatibleSchema: compatible);
    try
    {
        Success(await result.Schema.PrepareAsync(create ? new MetadataSchemaRequest.CreateIfEmpty() : new MetadataSchemaRequest.InspectOnly(), new(), default));
        return result;
    }
    catch { await result.DisposeAsync(); throw; }
}

switch (mode)
{
    case "seed-mutation":
        {
            await using var fixture = await Open(create: true);
            await Seed(fixture);
            Write("baseline-digest.json", Digest(await Read(fixture)));
            var ticket = Success(await fixture.Store.ReserveOperationAsync(new(), default));
            var entry = Entry(2);
            var batch = Batch(ticket, new MetadataMutation.PutPackage(Package(2), new ExpectedRevision.Absent()),
                new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), new("renewed-by-child")),
                new MetadataMutation.AcquireLease(new("maintenance-2"), Id(12), 300),
                new MetadataMutation.AddAggregateContribution(Aggregate(2), Delta(7)));
            Write("request.json", batch);
            Console.WriteLine("{\"seeded\":true}");
            break;
        }
    case "run-mutation":
        {
            await using var fixture = await Open();
            fixture.Controls.SetObserver(barrier, () => Hold(barrier));
            var receipt = Success(await fixture.Store.CommitAsync(RenewEvidence(fixture, Load<MetadataMutationBatch>("request.json")), new(TimeSpan.FromSeconds(30)), default));
            Write("acknowledged.json", receipt.CommitId);
            await Hold("M2");
            break;
        }
    case "recover-mutation":
        {
            await using var fixture = await Open();
            Require(Digest(await Read(fixture)) == Load<string>("baseline-digest.json"));
            var request = RenewEvidence(fixture, Load<MetadataMutationBatch>("request.json"));
            var group = await Read(fixture, 2);
            var resolution = Success(await fixture.Store.ReconcileAsync(request.Ticket, new(), default));
            if (barrier == "M0")
            {
                Require(group.Items.All(item => item is MetadataReadItem.NotFound));
                Require(resolution is MetadataResolution.NotCommitted);
                Require(await fixture.Store.CommitAsync(request, new(), default) is MetadataResult<MetadataCommitReceipt>.Failure { Code: MetadataFailureCode.Conflict });
            }
            else
            {
                Require(group.Items.All(item => item is MetadataReadItem.Found));
                Require(resolution is MetadataResolution.Committed);
                var receipt = ((MetadataResolution.Committed)resolution).Receipt;
                foreach (var revision in receipt.Revisions)
                {
                    var record = group.Items.OfType<MetadataReadItem.Found>().Single(item => item.Record.Selector == revision.Target).Record;
                    Require(revision.Revision is MetadataOption<MetadataRevision>.Some observed && observed.Value == record.Revision);
                }
                var artifact = group.Items.OfType<MetadataReadItem.Found>().Select(item => item.Record).OfType<MetadataArtifactState>().Single();
                var aggregate = group.Items.OfType<MetadataReadItem.Found>().Select(item => item.Record).OfType<MetadataAccessAggregate>().Single();
                Require(artifact.LiveReferences == 1 && aggregate.Counters.Hits == 7);
                Require(receipt.References.Single().Revision == artifact.Revision);
                Require(receipt.CommitId == Success(await fixture.Store.CommitAsync(request, new(), default)).CommitId);
                Require(Digest(group) == Digest(await Read(fixture, 2)));
                if (barrier == "M2") { Require(receipt.CommitId == Load<MetadataId>("acknowledged.json")); }
            }
            var settings = Success(await ((SqliteMetadataStore)fixture.Store).ConfigurationForTestAsync());
            Console.WriteLine(JsonSerializer.Serialize(new
            {
                barrier,
                baselineCompared = true,
                stateCompared = true,
                receiptCompared = true,
                settings,
                runtime = RuntimeInformation.FrameworkDescription,
                os = RuntimeInformation.OSDescription
            }));
            break;
        }
    case "seed-upgrade":
    case "seed-restore":
        {
            await using var fixture = await Open("fixture-sqlite-v1", create: true);
            await Seed(fixture);
            Write("baseline-digest.json", Digest(await Read(fixture)));
            var cursor = Success(await fixture.Store.ReadPageAsync(new MetadataPageQuery.Registries
            { PageSize = 1, Continuation = None<MetadataContinuation>() }, new(), default)).Continuation;
            Write("old-cursor.json", cursor);
            var baselineTicket = Success(await fixture.Store.ReserveOperationAsync(new(), default));
            Success(await fixture.Store.ReconcileAsync(baselineTicket, new(), default));
            Write("old-ticket.json", baselineTicket);
            var point = Success(await ((SqliteMetadataStore)fixture.Store).CaptureRecoveryPointAsync(new(), default));
            Write("recovery-point.json", point);
            Console.WriteLine("{\"seeded\":true}");
            break;
        }
    case "run-restore":
        {
            await using var fixture = await Open("fixture-sqlite-v1");
            fixture.Controls.SetObserver(barrier == "R0" ? "restore.after_native" : "restore.before_install", () => Hold(barrier));
            Success(await ((SqliteMetadataStore)fixture.Store).RestoreToIsolatedTargetAsync(
                Load<MetadataRecoveryPoint>("recovery-point.json"), FileAt("restored.db"),
                new HashSet<ArtifactDigest> { Entry().Digest }, new(), default));
            throw new InvalidOperationException("Restore did not stop at its installation barrier.");
        }
    case "recover-restore":
        {
            Require(!File.Exists(FileAt("restored.db")));
            await using var fixture = await Open("fixture-sqlite-v1");
            var point = Load<MetadataRecoveryPoint>("recovery-point.json");
            var admission = Success(await ((SqliteMetadataStore)fixture.Store).RestoreToIsolatedTargetAsync(point,
                FileAt("restored.db"), new HashSet<ArtifactDigest> { Entry().Digest }, new(), default));
            Require(admission.Epoch != point.Epoch);
            await using var restored = MetadataFixtureSession.Create("sqlite", new CrashClock(), FileAt("restored.db"), compatibleSchema: "fixture-sqlite-v1");
            Success(await restored.Schema.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), default));
            Require(Digest(await Read(restored)) == Load<string>("baseline-digest.json"));
            Require(await restored.Store.ReconcileAsync(Load<MetadataOperationTicket>("old-ticket.json"), new(), default)
                is MetadataResult<MetadataResolution>.Failure { Code: MetadataFailureCode.ReconciliationExpired });
            Console.WriteLine("{\"uninstalledTargetAbsent\":true,\"retryRestoredBaseline\":true,\"historicalTicketRejected\":true}");
            break;
        }
    case "run-upgrade":
        {
            await using var fixture = MetadataFixtureSession.Create("sqlite", new CrashClock(), database);
            var point = Load<MetadataRecoveryPoint>("recovery-point.json");
            fixture.Controls.SetObserver(barrier, () => Hold(barrier));
            var admitted = Success(await fixture.Schema.PrepareAsync(new MetadataSchemaRequest.Upgrade("fixture-sqlite-v1", "fixture-sqlite-v2", point), new(), default));
            Write("acknowledged.json", admitted.Epoch);
            await Hold("U4");
            break;
        }
    case "probe-upgrade":
        {
            await using var fixture = MetadataFixtureSession.Create("sqlite", new CrashClock(), database);
            var point = Load<MetadataRecoveryPoint>("recovery-point.json");
            var observed = ((SqliteMetadataStore)fixture.Store).ObserveIndependentLayoutForTest();
            Require(observed.Version == "fixture-sqlite-v1" && observed.LogicalDigest == point.LogicalDigest);
            Require(await fixture.Schema.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(TimeSpan.FromMilliseconds(50)), default)
                is MetadataResult<MetadataSchemaAdmission>.Failure);
            Console.WriteLine("{\"independentOldLayout\":true,\"admissionRejected\":true}");
            break;
        }
    case "recover-upgrade":
        {
            await using var fixture = MetadataFixtureSession.Create("sqlite", new CrashClock(), database);
            var point = Load<MetadataRecoveryPoint>("recovery-point.json");
            var inspection = Success(await fixture.Schema.InspectAsync(new(), default));
            var beforeCommit = barrier is "U0" or "U1" or "U2";
            Require(inspection.CurrentVersion == (beforeCommit ? "fixture-sqlite-v1" : "fixture-sqlite-v2"));
            var request = new MetadataSchemaRequest.Upgrade("fixture-sqlite-v1", "fixture-sqlite-v2", point);
            MetadataSchemaAdmission admission;
            if (beforeCommit) { admission = Success(await fixture.Schema.PrepareAsync(request, new(), default)); }
            else
            {
                Require(await fixture.Schema.PrepareAsync(request, new(), default) is MetadataResult<MetadataSchemaAdmission>.Failure);
                admission = Success(await fixture.Schema.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), default));
            }
            Require(admission.Epoch != point.Epoch);
            Require(Digest(await Read(fixture)) == Load<string>("baseline-digest.json"));
            Require(Success(await ((SqliteMetadataStore)fixture.Store).LogicalDigestForTestAsync()) == point.LogicalDigest);
            Require(await fixture.Store.ReconcileAsync(Load<MetadataOperationTicket>("old-ticket.json"), new(), default)
                is MetadataResult<MetadataResolution>.Failure { Code: MetadataFailureCode.ReconciliationExpired });
            Require(await fixture.Store.ReadPageAsync(new MetadataPageQuery.Registries
            { PageSize = 1, Continuation = Load<MetadataOption<MetadataContinuation>>("old-cursor.json") }, new(), default)
                is MetadataResult<MetadataPage>.Failure { Code: MetadataFailureCode.InvalidInput });
            if (barrier == "U4") { Require(admission.Epoch == Load<MetadataId>("acknowledged.json")); }
            Console.WriteLine(JsonSerializer.Serialize(new { barrier, baselineCompared = true, stateCompared = true, receiptCompared = true }));
            break;
        }
    case "hold-owner":
        {
            await using var fixture = await Open(create: true);
            await Hold("owner");
            break;
        }
    case "stuck-native":
        {
            var fixture = await Open(create: true);
            await Seed(fixture);
            var sqlite = (SqliteMetadataStore)fixture.Store;
            fixture.Controls.SetObserver("M1", () =>
            {
                sqlite.StallNativeCallForTest(() => Write("barrier.json", new { barrier = "native-step", pid = Environment.ProcessId }));
                return ValueTask.CompletedTask;
            });
            var entry = Entry(2);
            var ticket = Success(await fixture.Store.ReserveOperationAsync(new(), default));
            var request = RenewEvidence(fixture, Batch(ticket, new MetadataMutation.PutPackage(Package(2), new ExpectedRevision.Absent()),
                new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), new("renewed-by-child"))));
            Require(await fixture.Store.CommitAsync(request, new(TimeSpan.FromSeconds(5)), default)
                is MetadataResult<MetadataCommitReceipt>.Failure { Code: MetadataFailureCode.Uncertain });
            Require(fixture.Authority.ActiveGuards == 1);
            try { await fixture.DisposeAsync(); throw new InvalidOperationException("Live native work was disposed."); }
            catch (InvalidOperationException error) when (error.Message.Contains("cleanup incomplete", StringComparison.Ordinal))
            {
                Require(fixture.Controls.Diagnostics.Contains("metadata.cleanup_incomplete"));
                Require(fixture.Authority.ActiveGuards == 1);
                Require(await fixture.Store.ReserveOperationAsync(new(), default)
                    is MetadataResult<MetadataOperationTicket>.Failure { Code: MetadataFailureCode.Disposed });
                Write("cleanup.json", new { cleanupIncomplete = true, guardRetained = true, admissionRejected = true });
            }
            await Task.Delay(TimeSpan.FromMinutes(5));
            throw new TimeoutException("Parent did not terminate its native-call child.");
        }
    case "try-owner":
        {
            await using var fixture = MetadataFixtureSession.Create("sqlite", new CrashClock(), database);
            Require(await fixture.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(TimeSpan.FromMilliseconds(50)), default)
                is MetadataResult<MetadataSchemaAdmission>.Failure { Code: MetadataFailureCode.Unavailable });
            Console.WriteLine("{\"competingOwnerRejected\":true}");
            break;
        }
    case "reopen-owner":
        {
            await using var fixture = await Open();
            Console.WriteLine("{\"crashReleasedOwner\":true}");
            break;
        }
    case "recovery-walkthrough":
        {
            await using var fixture = await Open("fixture-sqlite-v1", create: true);
            await Seed(fixture);
            var baseline = Digest(await Read(fixture));
            var oldTicket = Success(await fixture.Store.ReserveOperationAsync(new(), default));
            var sqlite = (SqliteMetadataStore)fixture.Store;
            Require(await sqlite.CaptureRecoveryPointAsync(new(), default) is MetadataResult<MetadataRecoveryPoint>.Failure { Code: MetadataFailureCode.Conflict });
            Success(await fixture.Schema.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), default));
            Success(await fixture.Store.ReconcileAsync(oldTicket, new(), default));
            Require(File.Exists(database + "-wal") && new FileInfo(database + "-wal").Length > 0);
            var point = Success(await sqlite.CaptureRecoveryPointAsync(new(), default));
            var artifacts = new HashSet<ArtifactDigest> { Entry().Digest };
            var missingTarget = FileAt("missing-artifacts.db");
            Require(await sqlite.RestoreToIsolatedTargetAsync(point, missingTarget, new HashSet<ArtifactDigest>(), new(), default)
                is MetadataResult<MetadataSchemaAdmission>.Failure { Code: MetadataFailureCode.Unavailable });
            Require(!File.Exists(missingTarget));
            Require(await sqlite.RestoreToIsolatedTargetAsync(point with { ApplicationVersion = "foreign" },
                FileAt("foreign.db"), artifacts, new(), default) is MetadataResult<MetadataSchemaAdmission>.Failure);
            Require(await sqlite.RestoreToIsolatedTargetAsync(point with { Id = Id(999) },
                FileAt("missing.db"), artifacts, new(), default) is MetadataResult<MetadataSchemaAdmission>.Failure);
            Require(await sqlite.RestoreToIsolatedTargetAsync(point with { ProviderId = "foreign" },
                FileAt("foreign-provider.db"), artifacts, new(), default) is MetadataResult<MetadataSchemaAdmission>.Failure);
            using (var cancellation = new CancellationTokenSource())
            {
                var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
                fixture.Controls.SetObserver("restore.after_native", () =>
                {
                    cancellation.Cancel();
                    return new(release.Task.WaitAsync(TimeSpan.FromSeconds(10)));
                });
                var cancelled = FileAt("cancelled.db");
                try
                {
                    Require(await sqlite.RestoreToIsolatedTargetAsync(point, cancelled, artifacts, new(), cancellation.Token)
                        is MetadataResult<MetadataSchemaAdmission>.Failure { Code: MetadataFailureCode.CancelledBeforeCommit });
                    Require(!File.Exists(cancelled));
                    Require(!fixture.WhenIdleAsync().IsCompleted);
                    Require(await fixture.Schema.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), default)
                        is MetadataResult<MetadataSchemaAdmission>.Failure { Code: MetadataFailureCode.Unavailable });
                }
                finally
                {
                    release.TrySetResult();
                    await fixture.WhenIdleAsync();
                    fixture.Controls.RemoveObserver("restore.after_native");
                }
            }
            Success(await fixture.Schema.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), default));
            await Commit(fixture, new MetadataMutation.PutRegistry(Registry(77), new ExpectedRevision.Absent()));
            var destination = FileAt("restored-v1.db");
            var restoredAdmission = Success(await sqlite.RestoreToIsolatedTargetAsync(point, destination, artifacts, new(), default));
            Require(restoredAdmission.Epoch != point.Epoch && restoredAdmission.SchemaVersion == "fixture-sqlite-v1");
            await using (var restored = MetadataFixtureSession.Create("sqlite", new CrashClock(), destination, compatibleSchema: "fixture-sqlite-v1"))
            {
                Success(await restored.Schema.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), default));
                Require(Digest(await Read(restored)) == baseline);
                Require(Success(await ((SqliteMetadataStore)restored.Store).LogicalDigestForTestAsync()) == point.LogicalDigest);
                Require(Success(await restored.Store.ReadAsync(new([Registry(77).Selector]), new(), default)).Items.Single() is MetadataReadItem.NotFound);
                Require(await restored.Store.ReconcileAsync(oldTicket, new(), default)
                    is MetadataResult<MetadataResolution>.Failure { Code: MetadataFailureCode.ReconciliationExpired });
            }
            await fixture.Store.DisposeAsync();
            await using (var current = MetadataFixtureSession.Create("sqlite", new CrashClock(), database))
            {
                Require(await current.Schema.PrepareAsync(new MetadataSchemaRequest.Upgrade("fixture-sqlite-v1", "fixture-sqlite-v2", point), new(), default)
                    is MetadataResult<MetadataSchemaAdmission>.Failure { Code: MetadataFailureCode.Conflict });
            }
            Console.WriteLine("{\"cases\":[\"MP-36\",\"MP-44\",\"MP-45\"],\"positive\":true,\"negative\":true,\"walCaptured\":true,\"isolatedRestoreCompared\":true,\"artifactSetRequired\":true}");
            break;
        }
    default: throw new ArgumentException("Unknown fixed recovery scenario.");
}
