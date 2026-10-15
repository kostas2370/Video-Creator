const coverageFields = {
  input_tokens: "requests_with_input_tokens",
  output_tokens: "requests_with_output_tokens",
  total_tokens: "requests_with_tokens",
};

export function tokenMetric(row, field) {
  const reported = row[coverageFields[field]];
  return {
    label: row[field] == null ? "Unavailable" : row[field].toLocaleString(),
    note: reported > 0 && reported < row.requests
      ? `${reported.toLocaleString()} of ${row.requests.toLocaleString()} requests reported`
      : null,
  };
}
