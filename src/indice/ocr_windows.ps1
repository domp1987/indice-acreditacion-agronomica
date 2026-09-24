# OCR con el motor integrado de Windows (Windows.Media.Ocr), sin instalar nada.
# Uso: powershell -NoProfile -ExecutionPolicy Bypass -File ocr_windows.ps1 -Carpeta <pngs> -Salida <json> [-Idioma es-ES]
# Escribe un JSON {"archivo.png": ["línea 1", "línea 2", ...]}.
param(
    [Parameter(Mandatory = $true)][string]$Carpeta,
    [Parameter(Mandatory = $true)][string]$Salida,
    [string]$Idioma = 'es-ES'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime]

# Las API de WinRT son asíncronas; en Windows PowerShell se esperan con AsTask
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
function Esperar($op, [Type]$tipo) {
    $t = $asTask.MakeGenericMethod($tipo).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result
}

$motor = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($Idioma))
if ($null -eq $motor) { throw "El OCR de Windows no tiene instalado el idioma $Idioma" }

$res = [ordered]@{}
foreach ($png in Get-ChildItem -LiteralPath $Carpeta -Filter *.png | Sort-Object Name) {
    $archivo = Esperar ([Windows.Storage.StorageFile]::GetFileFromPathAsync($png.FullName)) ([Windows.Storage.StorageFile])
    $flujo = Esperar ($archivo.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $deco = Esperar ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($flujo)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bmp = Esperar ($deco.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $r = Esperar ($motor.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
    $res[$png.Name] = @($r.Lines | ForEach-Object { $_.Text })
    $flujo.Dispose()
}
$json = $res | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($Salida, $json, (New-Object System.Text.UTF8Encoding($false)))
