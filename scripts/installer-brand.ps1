$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$calixRoot = Split-Path -Parent $PSScriptRoot
$calixArt = Join-Path $calixRoot 'src-tauri\installer-assets'
$null = New-Item -ItemType Directory -Force -Path $calixArt
$mark = [System.Drawing.Image]::FromFile((Join-Path $calixRoot 'src-tauri\icons\icon.png'))
$image = [System.Drawing.Bitmap]::new(164,314)
$draw = [System.Drawing.Graphics]::FromImage($image)
$draw.Clear([System.Drawing.ColorTranslator]::FromHtml('#e5f2f0'))
$draw.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$draw.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$draw.DrawImage($mark,35,36,94,94)
$accent = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#086f73'))
$text = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#274f53'))
$title = [System.Drawing.Font]::new('Segoe UI',29,[System.Drawing.FontStyle]::Bold)
$small = [System.Drawing.Font]::new('Segoe UI',10)
$draw.DrawString('Calix',$title,$accent,22,145)
$draw.DrawString("Calculation &`nInteractive`nXpressions",$small,$text,16,214)
$image.Save((Join-Path $calixArt 'welcome.bmp'),[System.Drawing.Imaging.ImageFormat]::Bmp)
$draw.Dispose(); $image.Dispose()
$image = [System.Drawing.Bitmap]::new(150,57)
$draw = [System.Drawing.Graphics]::FromImage($image)
$draw.Clear([System.Drawing.Color]::White)
$draw.DrawImage($mark,7,7,42,42)
$header = [System.Drawing.Font]::new('Segoe UI',18,[System.Drawing.FontStyle]::Bold)
$draw.DrawString('Calix',$header,$accent,53,12)
$image.Save((Join-Path $calixArt 'header.bmp'),[System.Drawing.Imaging.ImageFormat]::Bmp)
$draw.Dispose(); $image.Dispose(); $mark.Dispose()
$accent.Dispose(); $text.Dispose(); $title.Dispose(); $small.Dispose(); $header.Dispose()
