# Exporta un PPTX a PDF con PowerPoint (automatización COM). Las diapositivas ocultas no se exportan.
# Uso: powershell -NoProfile -ExecutionPolicy Bypass -File pptx_a_pdf.ps1 -Pptx <archivo.pptx> -Pdf <archivo.pdf>
param(
    [Parameter(Mandatory = $true)][string]$Pptx,
    [Parameter(Mandatory = $true)][string]$Pdf
)
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject PowerPoint.Application
try {
    # Open(ruta, ReadOnly, Untitled, WithWindow)
    $pres = $app.Presentations.Open($Pptx, -1, 0, 0)
    try { $pres.SaveAs($Pdf, 32) }   # 32 = ppSaveAsPDF
    finally { $pres.Close() }
}
finally {
    $app.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
