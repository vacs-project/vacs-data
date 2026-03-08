# Position Configuration

Positions map VATSIM controller logins to entities recognized by vacs. When a controller logs into VATSIM with a particular callsign, frequency, and facility type, the position configuration determines which vacs position (if any) corresponds to that login.

Position configuration is stored in positions.toml or positions.json inside an FIR's dataset directory.

## File Location

```
dataset/{FIR_CODE}/positions.{toml|json}
```

## File Structure

The file must contain a single top-level array named `positions`.

TOML:

```toml
[[positions]]
# Position 1 definition

[[positions]]
# Position 2 definition
```

JSON representation:

```jsonc
{
  "positions": [
    {
      /* Position 1 definition */
    },
    {
      /* Position 2 definition */
    },
  ],
}
```

## Key Terms

- **Position** (in vacs): A mapped entity that vacs recognizes, corresponding to one or more VATSIM controller logins (e.g., `LOWW_TWR`, `LOVV_CTR`)
- **Position** (on VATSIM/sectorfile): A controller login on VATSIM, defined by callsign, frequency, and facility type
- **Callsign prefix**: The base identifier used to match controller logins when the callsign doesn't exactly match a position ID (e.g., `LOWW` matches `LOWW_TWR`, `LOWW_W_TWR`)
- **Facility type**: The VATSIM category for the position (e.g., TWR, APP, CTR)
- **Profile**: Optional configuration preset that can be loaded for a position

## Position Fields

Each position entry maps a VATSIM controller login to a vacs position.

| Field           | Type             | Required | Description                                                                                                         |
| :-------------- | :--------------- | :------- | :------------------------------------------------------------------------------------------------------------------ |
| `id`            | String           | Yes      | Unique identifier for this position in vacs (e.g., `LOWW_TWR`, `LOVV_CTR`). Must start with the FIR's country code. |
| `prefixes`      | Array of strings | Yes      | Callsign prefixes used to match VATSIM logins when the callsign doesn't exactly match the `id` (e.g., `["LOWW"]`).  |
| `frequency`     | String           | Yes      | Primary frequency in `XXX.XXX` format (e.g., `118.700`).                                                            |
| `facility_type` | String           | Yes      | VATSIM facility type. Must be one of the facility types listed below.                                               |
| `profile_id`    | String           | No       | Optional ID of the profile to load for this position.                                                               |

## Validation Rules

The following validation rules apply:

- `id` must be unique across the entire dataset
- `id` must start with the FIR's two-letter country code
- `prefixes`:
  - must contain at least one prefix
  - must not contain duplicates
- `frequency` must be in `XXX.XXX` format
- `facility_type` must be one of the valid facility types listed below
- If the `id` ends with a known facility type suffix (e.g., `_TWR`, `_APP`, `_GND`), it must match the `facility_type` field. For example, a position with `id = "LOWW_GND"` must have `facility_type = "GND"`, not `"TWR"`. This ensures consistent matching from VATSIM callsigns to vacs positions.

## Facility Types

The `facility_type` field must be one of the following VATSIM facility types:

| Type  | Description             |
| :---- | :---------------------- |
| `RMP` | Ramp                    |
| `DEL` | Delivery                |
| `GND` | Ground                  |
| `TWR` | Tower                   |
| `APP` | Approach                |
| `DEP` | Departure               |
| `CTR` | Enroute / Center        |
| `FSS` | Flight Service Station  |
| `RDO` | Radio                   |
| `FMP` | Traffic Flow Management |

## Callsign Prefix Matching

The `prefixes` field defines how VATSIM controller logins map to this vacs position when the VATSIM callsign doesn't exactly match the position `id`.

### Matching Logic

When a controller logs into VATSIM, vacs attempts to map their login (callsign, frequency, facility type) to a vacs position using the following process:

1. **Exact match**: First, vacs checks if a vacs position exists with an `id` that exactly matches the VATSIM callsign (case-insensitive)
   - If found AND the frequency and facility type also match, this vacs position is used immediately
   - Example: VATSIM login `LOWW_TWR` exactly matches vacs position ID `LOWW_TWR`

2. **Prefix match**: If no exact match is found, vacs searches for vacs positions where:
   - The frequency matches exactly
   - The facility type matches exactly
   - The VATSIM callsign starts with any of the position's defined prefixes
   - Example: VATSIM login `LOVV_NM_CTR` doesn't match any vacs position ID exactly, but maps to vacs position `LOVV_CTR` with prefix `LOVV` if the frequency and facility type also match

### Callsign Normalization

Before matching, callsigns are normalized:

- Double underscores (`__`) are replaced with single underscores (`_`)
- All characters are converted to uppercase
- Example: `loww__twr` becomes `LOWW_TWR`

## Common Pitfalls

When configuring positions, watch out for these issues:

- **Multiple matching positions**: If multiple positions have the same frequency, facility type, and matching prefixes, vacs cannot automatically determine a single correct position. Ensure your prefixes are specific enough to avoid ambiguous matches, otherwise users will have to manually select a position when connecting to vacs.
- **Frequency format**: Ensure frequencies use the `XXX.XXX` format with exactly three digits before and after the decimal point.
- **Frequency and facility type must match**: Even if a callsign matches a prefix, the position will only be selected if the frequency and facility type also match exactly.

## Examples

### Simple tower position

This example defines a basic tower position with a single callsign prefix.

```toml
[[positions]]
id = "LOWW_TWR"
prefixes = ["LOWW"]
frequency = "119.400"
facility_type = "TWR"
profile_id = "LOWW"
```

What this means in practice:

- Controllers logging in with callsigns like `LOWW_TWR` or `LOWW__TWR` will be recognized as this position
- When a controller logs into this position, vacs will load the `LOWW` profile if available

### Positions sharing frequency and facility type

This example demonstrates two positions sharing the same frequency and facility type.

```toml
[[positions]]
id = "LOWI_E_APP"
prefixes = ["LOWI"]
frequency = "119.275"
facility_type = "APP"
profile_id = "LOVV"

[[positions]]
id = "LOWI_S_APP"
prefixes = ["LOWI"]
frequency = "119.275"
facility_type = "APP"
profile_id = "LOVV"
```

What this means in practice:

- Both `LOWI_E_APP` and `LOWI_S_APP` share the same frequency and facility type
- If a controller logs in as `LOWI_E_APP`, they will be recognized as the East approach position
- If a controller logs in as `LOWI_S_APP`, they will be recognized as the South approach position
- If the controller's callsign does _not_ match any of these two position IDs exactly, vacs cannot determine which position to use and the user will be prompted to select between the two before they can connect

### Position without a profile

This example shows a position that does not load a profile.

```toml
[[positions]]
id = "LOWW_DEL"
prefixes = ["LOWW"]
frequency = "121.800"
facility_type = "DEL"
```

What this means in practice:

- The `profile_id` field is optional and can be omitted
- Controllers logging into this position will not have a profile automatically loaded
- Positions without profiles associated will only receive a basic view showing connected users (and their VATSIM callsign) and **will not show up as an online station for other controllers in vacs**

### Prefix matching with non-standard callsigns

This example demonstrates how prefix matching handles non-standard callsign suffixes.

```toml
[[positions]]
id = "LOWW_TWR"
prefixes = ["LOWW"]
frequency = "119.400"
facility_type = "TWR"
```

What this means in practice:

- A controller logging in as `LOWW_TWR` will match exactly (ID match)
- A controller logging in as `LOWW_NM_TWR` will match via prefix (starts with `LOWW`, same frequency and facility type)
- A controller logging in as `LOWW_1_TWR` (relief position) will also match via prefix
- However, a controller logging in as `LOWW_APP` with the same frequency will NOT match (different facility type)
- And a controller logging in as `LOWW_TWR` on frequency `123.800` will NOT match (different frequency)
