using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore
{
    public ValueTask<ArtifactResult<ArtifactStamp>> ValidateAsync(ArtifactCommitEvidence evidence,
        IArtifactProtectionGuard protection, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(evidence);
        ArgumentNullException.ThrowIfNull(protection);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync(ArtifactPhase.Verify, options.Deadline, ct, async token =>
        {
            var request = protection.Grant.Request;
            if (evidence.Stamp.Store != StoreIdentity || request.Operation != ArtifactProtectionOperation.Reference
                || request.Store != StoreIdentity || request.Digest != evidence.Stamp.Identity.Digest
                || request.Stamp is not ArtifactOption<ArtifactStamp>.Some expected || expected.Value != evidence.Stamp)
            { throw new LocalStateException(ArtifactFailureCode.Denied); }
            var result = await configuration!.Authority.RetainAsync(protection, request, options, token);
            if (result is not ArtifactResult<IArtifactProtectionGuard>.Success recognized)
            { throw new LocalStateException(ArtifactFailureCode.Denied); }
            await using var retention = recognized.Value;
            lock (stateSync)
            {
                if (!operations.TryGetValue(evidence.TicketId, out var operation) || operation.State != "committed"
                    || Now() >= operation.Expires || operation.Receipt != evidence.ReceiptId
                    || operation.Proof != evidence.ProofHandle || operation.Content!.Stamp(StoreIdentity) != evidence.Stamp
                    || (int)operation.Outcome != (int)evidence.Outcome)
                { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                if (!decisions.TryGetValue(evidence.Stamp.Identity.Digest.Hex, out var decision)
                    || decision.Removed || decision.Content.Stamp(StoreIdentity) != evidence.Stamp)
                { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                if (decision.Corrupt) { throw new LocalStateException(ArtifactFailureCode.CorruptContent); }
                using var direct = new FileStream(PayloadPath(decision.Content), FileMode.Open, FileAccess.Read, FileShare.Read);
                if (direct.Length != decision.Content.Length) { throw new LocalStateException(ArtifactFailureCode.CorruptContent); }
                token.ThrowIfCancellationRequested();
                return evidence.Stamp;
            }
        });
    }
}
