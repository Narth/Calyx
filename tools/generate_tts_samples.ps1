<#
Generate TTS sample WAV files for wake-word evaluation using Windows SAPI.

This script creates a small set of neutral TTS clips containing the target
word variants and some negative samples. It is intended to provide unbiased
synthetic data for quick testing. You may replace or augment these with your
own recorded voice files in `samples/wake_word/positive` and `samples/wake_word/negative`.

Run from the project root in PowerShell:
  .\tools\generate_tts_samples.ps1
#>

param()

Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repo = Resolve-Path "$root\.."
$posDir = Join-Path $repo "samples\wake_word\positive"
$negDir = Join-Path $repo "samples\wake_word\negative"
New-Item -ItemType Directory -Path $posDir -Force | Out-Null
New-Item -ItemType Directory -Path $negDir -Force | Out-Null

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer

function SpeakToFile($text, $outPath, $rate=0) {
    try {
        $synth.Rate = $rate
        $synth.SetOutputToWaveFile($outPath)
        $synth.Speak($text)
        $synth.SetOutputToDefaultAudioDevice()
        Write-Host "Wrote $outPath"
    } catch {
        Write-Warning "Failed to write $outPath : $_"
    }
}

# Positive examples (contain Calyx pronounced several ways)
SpeakToFile "Calyx" (Join-Path $posDir "calyx_pos_01.wav") 0
SpeakToFile "Hey Calyx, open terminal" (Join-Path $posDir "calyx_pos_02.wav") 0
SpeakToFile "Calyx" (Join-Path $posDir "calyx_pos_03_fast.wav") 2
SpeakToFile "Callyx" (Join-Path $posDir "calyx_pos_04_variant.wav") 0

# Negative examples (confusers and random speech)
SpeakToFile "Calix is a company name" (Join-Path $negDir "calix_neg_01.wav") 0
SpeakToFile "Kallax furniture is from IKEA" (Join-Path $negDir "kallax_neg_01.wav") 0
SpeakToFile "This is a sample sentence without the wake word" (Join-Path $negDir "random_neg_01.wav") 0
SpeakToFile "Kelly's restaurant is open" (Join-Path $negDir "kellys_neg_01.wav") 0

Write-Host "TTS sample generation finished. Inspect samples/wake_word/{positive,negative}."
