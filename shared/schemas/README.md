# Shared Schemas

This directory contains the source of truth for message schemas used across Loom's data pipelines.

## Guidelines

1. **JSON Schema First**: All message contracts are defined using [JSON Schema Draft 2020-12](https://json-schema.org/).
2. **Avro Derivatives**: For high-throughput topics, equivalent Avro schemas are generated automatically via CI.
3. **Versioning**: Use semantic versioning (`v{major}.{minor}.{patch}`) in the schema filename. Breaking changes bump the major version.
4. **Compatibility**: Schemas must remain **backward compatible** within a major version. CI will fail if backward compatibility is broken.
5. **Namespacing**: Mirror the Kafka topic hierarchy (e.g., `device/audio/raw/v1.json`).

## Directory Structure

```
shared/schemas/
└── device/
    └── audio/
        └── raw/
            ├── v1.json
            └── v2.json
```

## Adding a New Schema

1. Create a new file following the directory structure and naming convention.
2. Run `make validate-schemas` to ensure the schema is valid JSON and passes linting.
3. Commit the schema with a descriptive message (e.g., `feat(schema): add device.audio.raw v2`).
