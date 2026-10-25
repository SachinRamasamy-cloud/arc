/** A pure, browser-independent adapter for the currently published processing contract. */
import {parseData} from './core';

export type PlaygroundOperation = 'validate' | 'normalize' | 'csv_to_json' | 'json_to_csv';
export type FieldMapping = {source: string; target: string};
export type PlaygroundConfig = {
  operation: PlaygroundOperation;
  input: string;
  fileId?: string;
  requiredFields: string;
  lowercaseFields: string;
  mappings: FieldMapping[];
  maxCredits: string;
};

export class PlaygroundInputError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'PlaygroundInputError';
  }
}

const VALID_OPERATIONS: ReadonlySet<string> = new Set(['validate', 'normalize', 'csv_to_json', 'json_to_csv']);
const MAX_INLINE_BYTES = 1_500_000;

function fields(value: string): string[] {
  const result = value.split(',').map(field => field.trim()).filter(Boolean);
  if (result.length > 64 || result.some(field => field.length > 120)) {
    throw new PlaygroundInputError('Use at most 64 field names, each no longer than 120 characters.');
  }
  return [...new Set(result)];
}

function createMappings(entries: FieldMapping[]): Record<string, string> {
  if (entries.length > 64) throw new PlaygroundInputError('A maximum of 64 field mappings is supported.');
  const seenSources = new Set<string>();
  const seenTargets = new Set<string>();
  const valid: [string, string][] = [];
  for (const entry of entries) {
    const source = entry.source.trim();
    const target = entry.target.trim();
    if (!source || !target || source.length > 120 || target.length > 120) {
      throw new PlaygroundInputError('Every field mapping needs a valid source and destination name.');
    }
    if (seenSources.has(source) || seenTargets.has(target)) {
      throw new PlaygroundInputError('A source or destination field is used more than once.');
    }
    seenSources.add(source);
    seenTargets.add(target);
    valid.push([source, target]);
  }
  return Object.fromEntries(valid);
}

/** Validates and creates the exact Run JSON accepted by FastAPI. Never accepts raw API keys. */
export function buildPlaygroundRequest(config: PlaygroundConfig) {
  if (!VALID_OPERATIONS.has(config.operation)) {
    throw new PlaygroundInputError('The selected operation is not supported.');
  }
  const maxCredits = Number(config.maxCredits);
  if (!config.maxCredits.trim() || !Number.isFinite(maxCredits) || maxCredits < 0 || maxCredits > 1000 ||
      Math.abs(maxCredits * 1000 - Math.round(maxCredits * 1000)) > 1e-7) {
    throw new PlaygroundInputError('Enter a maximum cost between 0 and 1,000 credits, with up to three decimal places.');
  }
  if (config.fileId && !/^[A-Za-z0-9_-]{1,96}$/.test(config.fileId)) {
    throw new PlaygroundInputError('Select an available verified file.');
  }
  let data: unknown = null;
  if (!config.fileId) {
    if (!config.input.trim()) throw new PlaygroundInputError('Enter input data before running an operation.');
    if (new TextEncoder().encode(config.input).length > MAX_INLINE_BYTES) {
      throw new PlaygroundInputError('Inline input exceeds 1.5 MB. Upload a file instead.');
    }
    try {
      data = parseData(config.input, config.operation);
    } catch {
      throw new PlaygroundInputError(config.operation === 'csv_to_json'
        ? 'Enter valid CSV content with a header row.'
        : 'Enter valid JSON, or select CSV to JSON for CSV input.');
    }
  }
  return {
    operation: config.operation,
    data,
    file_id: config.fileId || null,
    required_fields: config.operation === 'validate' ? fields(config.requiredFields) : [],
    lowercase: config.operation === 'normalize' ? fields(config.lowercaseFields) : [],
    mappings: config.operation === 'normalize' ? createMappings(config.mappings) : {},
    max_credits_milli: Math.round(maxCredits * 1000),
  };
}

/** Used for UI field suggestions only; the backend remains responsible for validation. */
export function discoverFields(input: string, operation: PlaygroundOperation): string[] {
  if (operation === 'csv_to_json') {
    return input.split(/\r?\n/, 1)[0]?.split(',').map(s => s.trim()).filter(Boolean).slice(0, 64) ?? [];
  }
  try {
    const decoded = parseData(input, operation);
    const rows = Array.isArray(decoded) ? decoded : [decoded];
    const keys = new Set<string>();
    for (const row of rows.slice(0, 25)) {
      if (row && typeof row === 'object' && !Array.isArray(row)) {
        Object.keys(row).forEach(key => {if (keys.size < 64) keys.add(key);});
      }
    }
    return [...keys];
  } catch {
    return [];
  }
}
