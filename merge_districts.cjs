// This is Dave's updated script, based on our previous, that:
// 1. Copies all three tables (Incidents, Schools, Districts)
// 2. Fixes the links in the merged table

// ------------------------------
// CONFIGURATION: General
// ------------------------------

const dryRun = true; // << Change to false to actually copy
const state = "Michigan"; // This will find ADD-<state>-Incidents/Schools/Districts

const TABLE_IDENTIFIERS = ["Districts", "Schools", "Incidents"];

const UNIQUE_FIELD_NAMES = {
  Districts: "NCES-District-ID",
  Schools: "NCES-School-ID",
  Incidents: "Incident-Number",
};

/** Return a string like "ADD-Michigan-Incidents" */
function getSourceTableName(state, tableName) {
  return `ADD-${state}-${tableName}`;
}

const TARGET_TABLE_NAMES = {
  Districts: "District-Table",
  Schools: "School-Table",
  Incidents: "Incident-Table",
};

// ------------------------------
// CONFIGURATION: Field Mappings
// ------------------------------

const DISTRICTS_FIELD_MAPPING = [
  "District-Name",
  "District-State",
  "District-URL",
  "Board-URL",
  "District-Logo",
  "District-Twitter",
  "District-Facebook",
  "District-Phone",
  "School-Table",
  "Incident-Table",
  "INTERNAL-Notes",
];

// NOTE: Districts columns NOT included in copy:
//
// "Incident-Reports-URL" (not in ADD table)
// "Query-String" (not in ADD table)
// "Add-HTML" (not in ADD table)
// "All-District-Incidents-URL" (not in ADD table)
// "Last Modified By" (computed User; let airtable choose)
// "Last Modified" (want airtable to update)

const SCHOOLS_FIELD_MAPPING = [
  "School-Name",
  "School-State",
  "School-City",
  "School-Address",
  "School-URL",
  "School-Level",
];

// NOTE: Schools columns NOT included in copy:
//
// "School-Table" (think this was a mistake in previous script?)
// "LINKED-District-Name (District-Table)" (for linking only; can't copy direct)
// "LINKED-Incident-IDs" (for linking only; can't copy direct)
// "INTERNAL-Notes" (not in ADD table)

const INCIDENTS_FIELD_MAPPING = [
  "Incident-Number",
  "Year",
  "Month",
  "Day",
  "School-State",
  "School-City",
  "School-Name",
  "School-Level",
  "District-Name",
  "Incident-Type",
  "Incident-Summary",
  "Supporting-Materials",
  "Related-Link-1",
  "Related-Link-2",
  "Related-Link-3",
  "Reported-to-School",
  "School-Responded",
  "Dashboard-Access",
  "Source-Public",
  "Source-Internal",
  "Source-ID",
  "Incident-Status",
  "INTERNAL-Status-Detail",
  "Publish",
  "Detail-Page",
  "INTERNAL-Notes",
];

// NOTE: Incidents columns NOT included in copy:
//
// "LINKED-Schools (School-Table)" (for linking only; can't copy direct)
// "LINKED-Districts" (for linking only; can't copy direct)
// "Created By" (computed User; let airtable choose)
// "Created" (want airtable to update)

const FIELD_MAPPINGS = {
  Districts: DISTRICTS_FIELD_MAPPING,
  Schools: SCHOOLS_FIELD_MAPPING,
  Incidents: INCIDENTS_FIELD_MAPPING,
};

// ------------------------------
// CONFIGURATION: Table Linkages
// ------------------------------

const DISTRICT_LINKS = [
  {
    from: "LINKED-Schools (xSchools-Table)",
    to: "LINKED-Schools (School-Table)",
    linkToTableIdentifier: "Schools",
  },
  {
    from: "Incident-Table",
    to: "LINKED-Incident-IDs (Incident-Table)",
    linkToTableIdentifier: "Incidents",
  },
];

const SCHOOLS_LINKS = [
  {
    from: "LINKED-District (xDistrict-Table)",
    to: "LINKED-District (District-Table)",
    linkToTableIdentifier: "Districts",
  },
  {
    from: "LINKED-Incidents (xIncidents-Table)",
    to: "LINKED-Incident-IDs (Incident-Table)",
    linkToTableIdentifier: "Incidents",
  },
];

const INCIDENTS_LINKS = [
  {
    from: "LINKED-Schools (School-Table)",
    to: "LINKED-Schools (School-Table)",
    linkToTableIdentifier: "Schools",
  },
  {
    from: "LINKED-Districts (District-Table)",
    to: "LINKED-Districts (District-Table)",
    linkToTableIdentifier: "Districts",
  },
];

const LINKS = {
  Districts: DISTRICT_LINKS,
  Schools: SCHOOLS_LINKS,
  Incidents: INCIDENTS_LINKS,
};

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
// Primary copying code
// ------------------------------

/** Copy a single table from ADD to target, possibly in dry-run mode. */
async function copyTable(state, tableIdentifier) {
  const sourceTableName = getSourceTableName(state, tableIdentifier);
  const sourceTable = base.getTable(sourceTableName);
  const sourceRecords = await sourceTable.selectRecordsAsync();

  const targetTableName = TARGET_TABLE_NAMES[tableIdentifier];
  const targetTable = base.getTable(targetTableName);
  const targetRecords = await targetTable.selectRecordsAsync();

  const uniqueFieldName = UNIQUE_FIELD_NAMES[tableIdentifier];
  const fieldMapping = FIELD_MAPPINGS[tableIdentifier];

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

    // Map values from the "ADD" table to values suitable to inserting into the target table.
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
      TableIdentifier: tableIdentifier,
      Count: planned.length,
      Sample:
        planned.slice(0, 10).join(", ") + (planned.length > 10 ? "..." : ""),
    },
    {
      Status: "Skipped",
      TableIdentifier: tableIdentifier,
      Count: skipped.length,
      Sample:
        skipped.slice(0, 10).join(", ") + (skipped.length > 10 ? "..." : ""),
    },
  ]);
}

/** Copy all tables */
async function copyAllTables(state) {
  for (const tableIdentifier of TABLE_IDENTIFIERS) {
    await copyTable(state, tableIdentifier);
  }
}

// ------------------------------
// Primary linking code
// ------------------------------

/** Perform the real work of reconstituting links. */
async function linkSingleLinkage(state, tableIdentifier, linkage) {
  // The "source" table contains the TEXTUAL IDs that we want to use,
  // in the linkage.from column.
  const sourceTableName = getSourceTableName(state, tableIdentifier);
  const sourceTable = base.getTable(sourceTableName);
  const sourceRecords = await sourceTable.selectRecordsAsync();

  // The "target" table will need to contain actual links, in the
  // linkage.to column.
  const targetTableName = TARGET_TABLE_NAMES[tableIdentifier];
  const targetTable = base.getTable(targetTableName);
  const targetTableUniqueFieldName = UNIQUE_FIELD_NAMES[tableIdentifier];
  const targetTableRecords = await targetTable.selectRecordsAsync({
    fields: [targetTableUniqueFieldName],
  });

  // The linkage.linkToTableIdentifier can help us verify that every link
  // we try to create is going to be valid -- perfect for dry run mode
  const linkToTableName = TARGET_TABLE_NAMES[linkage.linkToTableIdentifier];
  const linkToTable = base.getTable(linkToTableName);
  const linkToRecords = await linkToTable.selectRecordsAsync();
  const linkToTableUniqueFieldName =
    UNIQUE_FIELD_NAMES[linkage.linkToTableIdentifier];
  let validLinkToIDs = new Set(
    linkToRecords.records
      .map((r) => r.getCellValue(linkToTableUniqueFieldName))
      .filter(Boolean)
  );

  // If we're doing a dry run, we didn't copy over the new identifiers; instead,
  // capture them here:
  if (dryRun) {
    const sourceLinkToTableName = getSourceTableName(
      state,
      linkage.linkToTableIdentifier
    );
    const sourceLinkToTable = base.getTable(sourceLinkToTableName);
    const sourceLinkToRecords = await sourceLinkToTable.selectRecordsAsync();
    const sourceValidLinkToIDs = new Set(
      sourceLinkToRecords.records
        .map((r) => r.getCellValue(linkToTableUniqueFieldName))
        .filter(Boolean)
    );
    validLinkToIDs = new Set([...validLinkToIDs, ...sourceValidLinkToIDs]);
  }

  let updates = [];
  let planned = [];
  for (const sourceRecord of sourceRecords.records) {
    const sourceRecordUniqueIdentifier = sourceRecord.getCellValue(
      targetTableUniqueFieldName
    );
    const targetRecord = targetTableRecords.records.find(
      (r) =>
        r.getCellValue(targetTableUniqueFieldName) ===
        sourceRecordUniqueIdentifier
    );
    const targetRecordId = targetRecord?.id ?? {
      id: `DRY-RUN-${sourceRecordUniqueIdentifier}`,
    };
    if (!targetRecord && !dryRun) {
      console.error(
        `Could not find identifier ${sourceRecordUniqueIdentifier} (found in ${sourceTableName}) in target table ${targetTableName}).`
      );
      throw new Error("abort");
    }

    const textualIdentifierList = sourceRecord.getCellValue(linkage.from) || "";
    const individualIdentifiers = textualIdentifierList
      .split(",")
      .map((i) => i.trim())
      .filter((i) => Boolean(i));

    if (individualIdentifiers.length === 0) {
      // nothing to link here
      continue;
    }

    // sanity check that we're linking to real things
    for (const ii of individualIdentifiers) {
      if (validLinkToIDs.has(ii)) {
        continue;
      }
      console.error(
        `Tried to create a link to invalid identifier: ${ii} found in ${sourceTableName} ${linkage.from}`
      );
      throw new Error("abort");
    }

    const nameArray = individualIdentifiers.map((ii) => ({ name: ii }));

    const fullLinkArray = [];

    // figure out the airtable record IDs for our own unique identifier; ugh, so much indirection.
    for (const nameObj of nameArray) {
      let airtableLinkToRecordId = `DRY-RUN-ID-${nameObj.name}`;
      if (!dryRun) {
        const targetLinkToRecord = linkToRecords.records.find(
          (r) => r.getCellValue(linkToTableUniqueFieldName) === nameObj.name
        );
        if (!targetLinkToRecord) {
          console.error(
            `Could not find link-to identifier ${nameObj.name} in link-to table ${linkToTableName}; fail`
          );
          throw new Error("abort");
        }
        airtableLinkToRecordId = targetLinkToRecord.id;
      }
      const finalObj = { id: airtableLinkToRecordId, name: nameObj.name };
      fullLinkArray.push(finalObj);
    }

    const updateData = {
      id: targetRecordId,
      fields: { [linkage.to]: fullLinkArray },
    };
    updates.push(updateData);
    planned.push(
      `${sourceRecordUniqueIdentifier} ==> ${individualIdentifiers.join(", ")}`
    );

    if (!dryRun && updates.length === 50) {
      await safeBatchUpdate(targetTable, updates);
      updates = [];
    }
  }

  // Process remaining batch, if any
  if (!dryRun && updates.length > 0) {
    await safeBatchUpdate(targetTable, updates);
  }

  // Output a summary of what happened
  if (dryRun) {
    output.markdown(`**Dry Run Mode** — No records were linked.`);
  } else {
    output.markdown(`**Copy Complete** — Records have been linked.`);
  }

  // Table summary for clarity
  output.table([
    ...planned
      .map((p) => ({
        Status: "Planned to link",
        TableIdentifier: tableIdentifier,
        LinkTableIdentifier: linkage.linkToTableIdentifier,
        Links: p,
      }))
      .slice(0, 10),
    {
      Status: "...",
      TableIdentifier: "...",
      LinkTableIdentifier: "...",
      Links: "...",
    },
  ]);
}

/** Perform all linkages for a given table identifier. */
async function linkTable(state, tableIdentifier) {
  const linkages = LINKS[tableIdentifier];
  for (const linkage of linkages) {
    await linkSingleLinkage(state, tableIdentifier, linkage);
  }
}

/** Link tables as needed */
async function linkAllTables(state) {
  for (const tableIdentifier of TABLE_IDENTIFIERS) {
    await linkTable(state, tableIdentifier);
  }
}

/** Perform all necessary processing for a state */
async function processAll(state) {
  await copyAllTables(state);
  await linkAllTables(state);
}

// ------------------------------
// Script main routine
// ------------------------------

// Do it ALL.
await processAll(state);
