const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export function getReportPdfUrl(scanId: string): string {
  return `${BASE_URL}/report/${scanId}/pdf`;
}

export async function downloadReport(scanId: string, token: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/report/${scanId}/pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error('Failed to download report');
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ats-report-${scanId}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
