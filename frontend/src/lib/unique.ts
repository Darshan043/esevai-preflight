export function uniqueById<T extends { id: string }>(rows: T[]): T[] {
  const seen = new Set<string>();
  const unique: T[] = [];
  for (const row of rows) {
    if (!row.id || seen.has(row.id)) {
      continue;
    }
    seen.add(row.id);
    unique.push(row);
  }
  return unique;
}
