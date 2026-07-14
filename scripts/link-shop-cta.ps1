# Link nav CTA buttons to shop calculator
$root = 'i:\Diamond v3'

Get-ChildItem -Path $root -Filter '*.html' -File | ForEach-Object {
  $c = Get-Content $_.FullName -Raw -Encoding UTF8
  $n = $c -replace 'class="btn btn-mint btn-calc" href="price\.html">價格試算', 'class="btn btn-mint btn-calc" href="shop/calculator/index.html">開始訂製'
  if ($n -ne $c) { Set-Content $_.FullName $n -Encoding UTF8 -NoNewline; Write-Host "root: $($_.Name)" }
}

$patterns = @(
  @{ Path = 'jewelry'; Href = '../shop/calculator/index.html' },
  @{ Path = 'series'; Href = '../../shop/calculator/index.html' },
  @{ Path = 'jewelry\rings'; Href = '../../shop/calculator/index.html?category=ring' },
  @{ Path = 'jewelry\necklaces'; Href = '../../shop/calculator/index.html?category=pendant' },
  @{ Path = 'jewelry\earrings'; Href = '../../shop/calculator/index.html?category=earring' },
  @{ Path = 'jewelry\bracelets'; Href = '../../shop/calculator/index.html?category=bracelet' }
)

foreach ($p in $patterns) {
  $dir = Join-Path $root $p.Path
  Get-ChildItem -Path $dir -Filter 'index.html' -File -ErrorAction SilentlyContinue | ForEach-Object {
    $c = Get-Content $_.FullName -Raw -Encoding UTF8
    $old = if ($p.Path -eq 'jewelry') { 'href="../price.html">價格試算' } else { 'href="../../price.html">價格試算' }
    $new = "href=`"$($p.Href)`">開始訂製"
    $n = $c.Replace("class=`"btn btn-mint btn-calc`" $old", "class=`"btn btn-mint btn-calc`" $new")
    if ($n -ne $c) { Set-Content $_.FullName $n -Encoding UTF8 -NoNewline; Write-Host "$($p.Path): $($_.Name)" }
  }
}

$productCats = @{
  'rings' = 'ring'
  'necklaces' = 'pendant'
  'earrings' = 'earring'
  'bracelets' = 'bracelet'
}
foreach ($cat in $productCats.Keys) {
  $dir = Join-Path $root "jewelry\$cat"
  Get-ChildItem -Path $dir -Directory | ForEach-Object {
    $file = Join-Path $_.FullName 'index.html'
    if (Test-Path $file) {
      $c = Get-Content $file -Raw -Encoding UTF8
      $href = "../../../shop/calculator/index.html?category=$($productCats[$cat])"
      $n = $c -replace 'class="btn btn-mint btn-calc" href="../../../price\.html">價格試算', "class=`"btn btn-mint btn-calc`" href=`"$href`">開始訂製"
      if ($n -ne $c) { Set-Content $file $n -Encoding UTF8 -NoNewline; Write-Host "product: $cat/$($_.Name)" }
    }
  }
}

Write-Host 'Done'
