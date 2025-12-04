// This is Dave and Josh's attempt at merging NCES districts into the primary District-Table

// ------------------------------
// CONFIGURATION: General
// ------------------------------

const dryRun = true; // << Change to false to actually copy

const MERGE_FROM = "NCES-District-Import";
const MERGE_TO = "District-Table";

const UNIQUE_FIELD_NAME = "NCES-District-ID";

// ------------------------------
// CONFIGURATION: Field Mappings
// ------------------------------

const DISTRICTS_FIELD_MAPPING = [
  "District-Name",
  "District-State",
  "District-City",
  "District-Address",
  "District-URL",
  "District-Phone",
  "State-District-ID",
  "District-County",
  "District-Students",
  "District-Teachers",
  "District-Schools",
  "NCES-Locale",
  "NCES-Type",
  "Data-Source-Date",
  //   "District-Logo-Link"
];

// ------------------------------
// Utility code
// ------------------------------

/** Return true if the value is defined. */
function isDefined(value) {
  return value !== null && value !== undefined;
}

/** Map a value from the ADD table to one suitable for inserting in the target table. */
function mapCellValue(value) {
  // Map attachments
  if (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((v) => "url" in v)
  ) {
    return value.map((att) => ({ url: att.url }));
  }

  // Map multi-selects
  if (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((v) => "name" in v)
  ) {
    return value.map((v) => ({ name: v.name }));
  }

  // Map named objects (but don't carry over their id baggage)
  if (value && typeof value === "object" && "name" in value) {
    return { name: value.name };
  }

  // Map linked objects (carry over their id, since we've got nothing better to do)
  if (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((v) => "id" in v)
  ) {
    return value.map((v) => ({ id: v.id }));
  }

  return value;
}

/** Attempt to create a batch of records. Log an exception if one happens, then raise it outward. */
async function safeBatchCreate(table, records) {
  try {
    await table.createRecordsAsync(records);
  } catch (err) {
    console.error("Batch create failed: ", err.message);
    console.debug(records);
    throw err;
  }
}

/** Attempt to update a batch of records. Log an exception if one happens, then raise it outward. */
async function safeBatchUpdate(table, records) {
  try {
    await table.updateRecordsAsync(records);
  } catch (err) {
    console.error("Batch update failed: ", err.message);
    console.debug(records);
    throw err;
  }
}

// ------------------------------
// Primary copying and merging code
// ------------------------------

/**
 * Merge districts whose identifiers are currently in the target table.
 *
 * Do not overwrite cells in the target table that already have values.
 */
async function mergeExistingDistricts() {
  const sourceTableName = MERGE_FROM;
  const sourceTable = base.getTable(sourceTableName);
  const sourceRecords = await sourceTable.selectRecordsAsync();

  const targetTableName = MERGE_TO;
  const targetTable = base.getTable(targetTableName);
  const targetRecords = await targetTable.selectRecordsAsync();

  const uniqueFieldName = UNIQUE_FIELD_NAME;
  const fieldMapping = DISTRICTS_FIELD_MAPPING;

  const existingIDs = new Set(
    targetRecords.records
      .map((r) => r.getCellValue(uniqueFieldName))
      .filter(Boolean)
  );

  let recordsToUpdate = [];

  for (const record of sourceRecords.records) {
    const uniqueIdentifier = record.getCellValue(uniqueFieldName);

    // Only process records that already exist in the target table
    if (!uniqueIdentifier || !existingIDs.has(uniqueIdentifier)) {
      continue;
    }

    // Find the corresponding target record
    const targetRecord = targetRecords.records.find(
      (r) => r.getCellValue(uniqueFieldName) === uniqueIdentifier
    );
    if (!targetRecord) {
      console.error(`Target record with ID '${uniqueIdentifier}' not found`);
      throw new Error("abort");
    }

    // Map values from the "NCES" table to values suitable to updating the target table.
    // Only update fields that are currently empty in the target record.
    const updatedFields = {};

    for (const fieldName of fieldMapping) {
      if (!sourceTable.getField(fieldName)) {
        console.error(`Field '${fieldName}' not found in source table`);
        throw new Error("abort");
      }

      const sourceValue = record.getCellValue(fieldName);
      const targetValue = targetRecord.getCellValue(fieldName);
      if (isDefined(sourceValue) && !isDefined(targetValue)) {
        const mappedValue = mapCellValue(sourceValue);
        updatedFields[fieldName] = mappedValue;
      } else if (isDefined(targetValue) && fieldName === "Data-Source-Date") {
        // Special case: update Data-Source-Date even if it exists by
        // appending ", NCES-November-2025"
        updatedFields[fieldName] = targetValue + ", NCES-November-2025";
      }
    }

    // If there are fields to update, do so
    if (Object.keys(updatedFields).length > 0) {
      updatedFields[uniqueFieldName] = uniqueIdentifier; // Ensure the unique ID is included

      recordsToUpdate.push({
        id: targetRecord.id,
        fields: updatedFields,
      });

      // Batch every 50
      if (!dryRun && recordsToUpdate.length === 50) {
        await safeBatchUpdate(targetTable, recordsToUpdate);
        recordsToUpdate = [];
      }
    }
  }

  // Process remaining batch, if any
  if (!dryRun && recordsToUpdate.length > 0) {
    await safeBatchUpdate(targetTable, recordsToUpdate);
  }

  // Output a summary of what happened
  if (dryRun) {
    output.markdown(`**Dry Run Mode** — No records were updated.`);
  } else {
    output.markdown(`**Merge Complete** — Records have been updated.`);
  }

  // summarize a single record to update based on fields
  const summarizeUpdate = (record) => {
    const fields = Object.keys(record.fields).filter(
      (f) => f !== uniqueFieldName
    );
    return `${record.fields[uniqueFieldName]} (fields: ${fields.join(", ")})`;
  };

  // Table summary for clarity
  output.table([
    {
      Status: "Updated",
      TableIdentifier: "Districts",
      Count: recordsToUpdate.length,
      Sample:
        recordsToUpdate.slice(0, 5).map(summarizeUpdate).join(", ") +
        (recordsToUpdate.length > 5 ? "..." : ""),
    },
  ]);
}

/**
 * Copy all districts from the NCES table to the target, possibly in dry-run mode. */
async function copyNewDistricts() {
  const sourceTableName = MERGE_FROM;
  const sourceTable = base.getTable(sourceTableName);
  const sourceRecords = await sourceTable.selectRecordsAsync();

  const targetTableName = MERGE_TO;
  const targetTable = base.getTable(targetTableName);
  const targetRecords = await targetTable.selectRecordsAsync();

  const uniqueFieldName = UNIQUE_FIELD_NAME;
  const fieldMapping = DISTRICTS_FIELD_MAPPING;

  const existingIDs = new Set(
    targetRecords.records
      .map((r) => r.getCellValue(uniqueFieldName))
      .filter(Boolean)
  );

  let recordsToCreate = [];
  let skipped = [];
  let planned = [];

  for (const record of sourceRecords.records) {
    const uniqueIdentifier = record.getCellValue(uniqueFieldName);

    // Skip missing or duplicate IDs
    if (!uniqueIdentifier || existingIDs.has(uniqueIdentifier)) {
      skipped.push(uniqueIdentifier || "(Missing ID)");
      continue;
    }

    // Map values from the "NCES" table to values suitable to inserting into the target table.
    const newRecord = {};
    newRecord[uniqueFieldName] = uniqueIdentifier;

    for (const fieldName of fieldMapping) {
      if (!sourceTable.getField(fieldName)) {
        console.error(`Field '${fieldName}' not found in source table`);
        throw new Error("abort");
      }

      const value = record.getCellValue(fieldName);
      const mappedValue = mapCellValue(value);
      if (isDefined(mappedValue)) {
        newRecord[fieldName] = mappedValue;
      }
    }

    recordsToCreate.push({ fields: newRecord });
    planned.push(uniqueIdentifier);
    existingIDs.add(uniqueIdentifier);

    // Batch every 50
    if (!dryRun && recordsToCreate.length === 50) {
      await safeBatchCreate(targetTable, recordsToCreate);
      recordsToCreate = [];
    }
  }

  // Process remaining batch, if any
  if (!dryRun && recordsToCreate.length > 0) {
    await safeBatchCreate(targetTable, recordsToCreate);
  }

  // Output a summary of what happened
  if (dryRun) {
    output.markdown(`**Dry Run Mode** — No records were created.`);
  } else {
    output.markdown(`**Copy Complete** — Records have been created.`);
  }

  // Table summary for clarity
  output.table([
    {
      Status: "Planned to Copy",
      TableIdentifier: "Districts",
      Count: planned.length,
      Sample:
        planned.slice(0, 10).join(", ") + (planned.length > 10 ? "..." : ""),
    },
    {
      Status: "Skipped",
      TableIdentifier: "Districts",
      Count: skipped.length,
      Sample:
        skipped.slice(0, 10).join(", ") + (skipped.length > 10 ? "..." : ""),
    },
  ]);
}

async function copyAndMergeDistricts() {
  await mergeExistingDistricts();
  await copyNewDistricts();
}

// ------------------------------
// Script main routine
// ------------------------------

// Do it ALL.
await copyAndMergeDistricts();
