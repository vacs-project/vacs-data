# vacs Dataset Documentation

This dataset configures the relationships between stations, positions, and profiles, defining the communication setup for controllers in a centralized and structured manner.

This repository is primarily intended for NAV team members and contributors who want to define or maintain how controllers communicate within their FIR using [`vacs`](https://github.com/vacs-project/vacs). It is not intended for end users, who should instead refer to the main [`vacs`](https://github.com/vacs-project/vacs) repository for information on how to use [`vacs`](https://github.com/vacs-project/vacs).

## Directory Structure

The dataset is organized by FIR code in the [`dataset/`](../../dataset/) directory. Each FIR has its own subdirectory named after its ICAO prefix (e.g., `LO` for Austria, `ED` for Germany).

```
dataset/
├── {FIR_CODE}/
│   ├── stations.{toml|json}          # Station definitions
│   ├── positions.{toml|json}         # Position definitions
│   └── profiles/                     # Profile configurations (one or more per FIR)
│       ├── {PROFILE_ID}.{toml|json}
│       └── ...
└── ...
```

## Core Concepts

At a high level: a controller connects as a **position**, which controls one or more **stations**, and is presented with a **profile** defining their UI and available calls.

The dataset consists of three main components:

1.  **[Stations](./stations.md)**: Represents a specific frequency, service, or sector (e.g., `LOWW_TWR`, `LOVV_N1`, `LOVV_N2`). On VATSIM, it is common for a single controller to control multiple stations simultaneously, especially on APP/CTR positions where real-world sector granularity is often simplified.
2.  **[Positions](./positions.md)**: Represents a position, directly tied to a controller login (e.g., `LOWW_TWR`, `LOVV_CTR`). A position is what a user connects as, similar to the positions defined in sectorfiles, and represents the controller’s identity on the network. One position can control multiple stations.
3.  **[Profiles](./profiles.md)**: Defines the UI layout and available stations to call for a specific position or set of positions. Depending on the position they connect as, a user is automatically served the appropriate profile and will have the defined stations available to call.

## File Formats

Configuration files can be written in either **[TOML](https://toml.io/en/)** or **[JSON](https://www.json.org/json-en.html)**. The examples in this documentation will primarily use TOML for readability, but JSON is fully supported and often preferred (e.g., for complex profile layouts). TOML is generally recommended for simple configurations, while JSON may be more convenient for complex or deeply nested profile layouts.

Various tools exist to help you create and edit TOML files, with [Visual Studio Code](https://code.visualstudio.com/) being a popular editor of choice with good support for both TOML and JSON.

If you are using [Visual Studio Code](https://code.visualstudio.com/), you can use the [Even Better TOML](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml) extension to get syntax highlighting and validation for TOML files. JSON support is built-in natively.

If your tool of choice supports [JSON Schema](https://json-schema.org/), you can find the schemas for all dataset configurations in the [`docs/schemas`](../schemas/) directory or on GitHub:

- [stations.schema.json](../schemas/stations.schema.json) or [GitHub](https://raw.githubusercontent.com/vacs-project/vacs-data/refs/heads/main/docs/schemas/stations.schema.json)
- [positions.schema.json](../schemas/positions.schema.json) or [GitHub](https://raw.githubusercontent.com/vacs-project/vacs-data/refs/heads/main/docs/schemas/positions.schema.json)
- [profiles.schema.json](../schemas/profiles.schema.json) or [GitHub](https://raw.githubusercontent.com/vacs-project/vacs-data/refs/heads/main/docs/schemas/profiles.schema.json)
