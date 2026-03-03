# vacs-data Tools

This directory contains the CLI tools for managing the `vacs-data` repository. These tools are used to validate the dataset's integrity and import data from various sources.

## Installation

### Pre-built Binaries

You can download pre-built binaries for Linux, Windows, and macOS from the [GitHub Releases](https://github.com/vacs-project/vacs-data/releases/latest) page.

## Usage

### Validation

To validate the entire dataset:

```bash
vacs-data validate path/to/dataset
```

### Import

The tool supports importing data from other formats.

**VATglasses:**

```bash
vacs-data import vatglasses --input lo.json --output dataset/LO
```

**EuroScope:**

```bash
vacs-data import euroscope --input LOVV.ese --output dataset/LO --prefixes LO
```

You can run any command with `--help` to display a brief help message and show all available options.

## Development

The tools are written in Rust and organized as a Cargo workspace.

- `tools/cli`: The main CLI application.
- `tools/validator`: Core validation logic.
- `tools/importer`: Logic for importing data from external formats.
- `tools/diagnostics`: Shared logging and diagnostics.

To build and run locally:

```bash
cargo run --bin vacs-data -- --help
```

## License

The code in this `tools/` directory is licensed under either of:

- Apache License, Version 2.0 ([LICENSE-APACHE](../LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
- MIT license ([LICENSE-MIT](../LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.
