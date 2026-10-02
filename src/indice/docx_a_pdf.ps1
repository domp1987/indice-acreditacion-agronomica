# Exporta un DOCX a PDF con Word (automatización COM), para leer los PAD que llegan en Word.
# Uso: powershell -NoProfile -ExecutionPolicy Bypass -File docx_a_pdf.ps1 -Docx <archivo.docx> -Pdf <archivo.pdf>
param(
    [Parameter(Mandatory = $true)][string]$Docx,
    [Parameter(Mandatory = $true)][string]$Pdf
)
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject Word.Application
$app.Visible = $false
$app.DisplayAlerts = 0
try {
    # Open(FileName, ConfirmConversions, ReadOnly)
    $doc = $app.Documents.Open($Docx, $false, $true)
    try { $doc.ExportAsFixedFormat($Pdf, 17) }   # 17 = wdExportFormatPDF
    finally { $doc.Close($false) }
}
finally {
    $app.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
