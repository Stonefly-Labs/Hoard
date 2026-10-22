using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Memory;

public sealed partial class MemoryMetadataStore
{
    private async ValueTask<MetadataResult<MetadataSchemaInspection>> InspectCoreAsync(MemoryActivity activity)
    {
        await observe("schema.inspect");
        activity.Check();
        var captured = Volatile.Read(ref state);
        if (captured.Schema == applicationSchema)
        {
            return Success(new MetadataSchemaInspection(MetadataSchemaState.Compatible, "fixture.metadata.memory",
            $"fixture-memory-v{applicationSchema}", $"fixture-memory-v{applicationSchema}", MetadataSchemaAction.Admit));
        }
        return captured.Schema switch
        {
            0 => Success(new MetadataSchemaInspection(MetadataSchemaState.Empty, "fixture.metadata.memory", "", "fixture-memory-v2", MetadataSchemaAction.CreateExplicitly)),
            1 when applicationSchema == 2 => Success(new MetadataSchemaInspection(MetadataSchemaState.UpgradeRequired, "fixture.metadata.memory", "fixture-memory-v1", "fixture-memory-v2", MetadataSchemaAction.UpgradeWithRecoveryPoint)),
            2 => Success(new MetadataSchemaInspection(MetadataSchemaState.Incompatible, "fixture.metadata.memory", "fixture-memory-v2", "fixture-memory-v1", MetadataSchemaAction.UseCompatibleApplication)),
            3 => Success(new MetadataSchemaInspection(MetadataSchemaState.Incompatible, "fixture.metadata.memory", "unsupported", "fixture-memory-v2", MetadataSchemaAction.UseCompatibleApplication)),
            _ => Failure<MetadataSchemaInspection>(MetadataFailureCode.CorruptState, MetadataPhase.Schema)
        };
    }

    private async ValueTask<MetadataResult<MetadataSchemaAdmission>> PrepareCoreAsync(MetadataSchemaRequest request, MemoryActivity activity)
    {
        MetadataEncoding.Validate(request);
        await EnterWriterAsync(activity);
        try
        {
            var current = state;
            switch (current.Schema)
            {
                case 0 when request is MetadataSchemaRequest.CreateIfEmpty:
                    activity.CommitDecision();
                    Volatile.Write(ref state, current with { Schema = applicationSchema });
                    activity.Committed();
                    break;
                case var schema when schema == applicationSchema && request is not MetadataSchemaRequest.Upgrade: break;
                case 1 when applicationSchema == 2 && request is MetadataSchemaRequest.Upgrade upgrade:
                    if (upgrade.ExpectedCurrent != "fixture-memory-v1" || upgrade.Target != "fixture-memory-v2"
                        || logicalAuthorization is null || upgrade.VerifiedRecoveryPoint != logicalAuthorization
                        || authorizationChange != current.Changes)
                    { throw new MemoryContractFailure(MetadataFailureCode.InvalidInput); }
                    var now = Now(current);
                    foreach (var operation in current.Operations.Values)
                    {
                        activity.Check();
                        if (operation.State == 0 && operation.Ticket.Expires.UnixMilliseconds > now)
                        { throw new MemoryContractFailure(MetadataFailureCode.Conflict); }
                    }
                    await observe("memory.upgrade.before_decision");
                    activity.CommitDecision();
                    Volatile.Write(ref state, current with { Schema = 2, Epoch = new(Guid.NewGuid()), TimeFloor = now });
                    activity.Committed();
                    logicalAuthorization = null;
                    break;
                case 4: throw new MemoryContractFailure(MetadataFailureCode.CorruptState);
                default: throw new MemoryContractFailure(MetadataFailureCode.IncompatibleSchema);
            }
            lock (activitiesLock) { if (!disposed) { admitted = true; } }
            await observe("schema.admitted");
            return Success(new MetadataSchemaAdmission("fixture.metadata.memory", $"fixture-memory-v{applicationSchema}", state.Epoch, false));
        }
        finally { writer.Release(); }
    }

    public MetadataRecoveryPoint AuthorizeLogicalUpgrade()
    {
        lock (activitiesLock)
        {
            if (disposed || activities.Count != 0 || state.Schema != 1)
            { throw new InvalidOperationException("Logical upgrade authorization requires an idle old-schema fixture."); }
            authorizationChange = state.Changes;
            logicalAuthorization = new(new(Guid.NewGuid()), state.Epoch, "fixture.metadata.memory",
                "fixture-memory-v1", "fixture-memory-logical-only", "logical-only-not-a-durable-recovery-point");
            return logicalAuthorization;
        }
    }
}
