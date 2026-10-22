CREATE TABLE metadata_schema (
    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
    version TEXT NOT NULL,
    epoch BLOB NOT NULL CHECK(length(epoch)=16),
    time_floor INTEGER NOT NULL CHECK(time_floor>=0),
    change_number INTEGER NOT NULL CHECK(change_number>=0),
    recovery_annotation TEXT
);
CREATE INDEX metadata_schema_recovery ON metadata_schema(recovery_annotation);
CREATE TABLE metadata_records (
    key BLOB PRIMARY KEY NOT NULL,
    kind INTEGER NOT NULL CHECK(kind BETWEEN 1 AND 7),
    registry BLOB,
    package BLOB,
    policy BLOB,
    ecosystem BLOB,
    payload TEXT NOT NULL
) WITHOUT ROWID;
CREATE INDEX metadata_records_registry ON metadata_records(registry,kind);
CREATE INDEX metadata_records_package ON metadata_records(package);
CREATE INDEX metadata_records_policy ON metadata_records(policy);
CREATE TABLE metadata_edges (
    entry BLOB PRIMARY KEY NOT NULL,
    digest BLOB NOT NULL,
    FOREIGN KEY(entry) REFERENCES metadata_records(key) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(digest) REFERENCES metadata_records(key) DEFERRABLE INITIALLY DEFERRED
) WITHOUT ROWID;
CREATE INDEX metadata_edges_digest ON metadata_edges(digest);
CREATE TABLE metadata_operations (
    id BLOB PRIMARY KEY NOT NULL CHECK(length(id)=16),
    epoch BLOB NOT NULL CHECK(length(epoch)=16),
    issued INTEGER NOT NULL,
    expires INTEGER NOT NULL,
    state INTEGER NOT NULL CHECK(state BETWEEN 0 AND 2),
    fingerprint BLOB,
    receipt TEXT
) WITHOUT ROWID;
CREATE INDEX metadata_operations_expiry ON metadata_operations(expires);
