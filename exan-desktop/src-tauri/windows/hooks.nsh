; Exan installer additions, included by Tauri's NSIS template (bundle.windows.nsis.installerHooks).
;
; 1. A "reading model" page after the folder page (inserted by windows/installer.nsi, which is Tauri's
;    template plus two marked lines): the user picks one of the built-in models - the recommended,
;    smallest one is preselected - and must agree to its download. "Do not download now" skips it.
; 2. After the files are copied, NSIS_HOOK_POSTINSTALL runs `exan-sidecar.exe models download <id> --select`;
;    its progress lines appear in the installer's detail list. The installer itself contains no model.
;    If the download fails (for example offline), Exan offers the same model again on its first start.
;
; Unattended installs (/S or /P) show no pages; IT staff can pass /MODEL=<id> to download a model anyway.

!include nsDialogs.nsh
!include LogicLib.nsh
!include "${__FILEDIR__}\models.nsh"

Var ExanModel
Var ExanSkipRadio
Var ExanConsentBox

; Expanded by installer.nsi at the page position, after the template declared $PassiveMode and $UpdateMode.
!macro EXAN_MODEL_PAGE
  Page custom ExanModelPage ExanModelPageLeave

  Function ExanModelPage
    ${If} $PassiveMode = 1
    ${OrIf} $UpdateMode = 1
      Abort
    ${EndIf}
    !insertmacro MUI_HEADER_TEXT "$(exanPageTitle)" "$(exanPageSubtitle)"
    nsDialogs::Create 1018
    Pop $0
    ${If} $0 == error
      Abort
    ${EndIf}
    ${NSD_CreateLabel} 0 0 100% 18u "$(exanPageIntro)"
    Pop $0
    !insertmacro EXAN_MODEL_RADIOS
    ${NSD_CreateRadioButton} 0 ${EXAN_SKIP_Y} 100% 10u "$(exanSkip)"
    Pop $ExanSkipRadio
    ${NSD_CreateCheckbox} 0 ${EXAN_CONSENT_Y} 100% 22u "$(exanConsent)"
    Pop $ExanConsentBox
    ${NSD_AddStyle} $ExanConsentBox ${BS_MULTILINE}

    ${If} $ExanModel != ""
      ; Back on this page: keep the earlier choice and consent.
      !insertmacro EXAN_MODEL_CHECK $ExanModel
      ${NSD_Check} $ExanConsentBox
    ${Else}
      ; Models already downloaded (reinstall or update): preselect "do not download".
      ${DirState} "$LOCALAPPDATA\${BUNDLEID}\models" $0
      ${If} $0 = 1
        ${NSD_Check} $ExanSkipRadio
      ${Else}
        !insertmacro EXAN_MODEL_CHECK "${EXAN_RECOMMENDED_MODEL}"
      ${EndIf}
    ${EndIf}
    nsDialogs::Show
  FunctionEnd

  Function ExanModelPageLeave
    !insertmacro EXAN_MODEL_SELECTED $ExanModel
    ${If} $ExanModel != ""
      ${NSD_GetState} $ExanConsentBox $0
      ${If} $0 != ${BST_CHECKED}
        MessageBox MB_ICONINFORMATION|MB_OK "$(exanConsentNeeded)"
        StrCpy $ExanModel ""
        Abort
      ${EndIf}
    ${EndIf}
  FunctionEnd
!macroend

!macro NSIS_HOOK_POSTINSTALL
  ${If} $ExanModel == ""
    ClearErrors
    ${GetOptions} $CMDLINE "/MODEL=" $0
    ${IfNot} ${Errors}
      StrCpy $ExanModel $0
    ${EndIf}
  ${EndIf}
  ${If} $ExanModel != ""
    DetailPrint "$(exanDownloadStart)"
    StrCpy $1 "en"
    ${If} $LANGUAGE = 1031
      StrCpy $1 "de"
    ${EndIf}
    nsExec::ExecToLog '"$INSTDIR\exan-sidecar.exe" models download "$ExanModel" --select --models-dir "$LOCALAPPDATA\${BUNDLEID}\models" --data-dir "$APPDATA\${BUNDLEID}" --lang $1'
    Pop $0
    ${If} $0 != 0
      DetailPrint "$(exanDownloadFailed)"
      MessageBox MB_ICONEXCLAMATION|MB_OK "$(exanDownloadFailed)" /SD IDOK
    ${EndIf}
  ${EndIf}
!macroend

; Expanded by installer.nsi after the languages are loaded.
!macro EXAN_LANG_STRINGS
  LangString exanPageTitle ${LANG_ENGLISH} "Reading model"
  LangString exanPageSubtitle ${LANG_ENGLISH} "Choose the model that reads the photos of the answer sheets."
  LangString exanPageIntro ${LANG_ENGLISH} "Exan reads photos with a small model that runs on this PC. It is not part of this installer: the model you choose is downloaded once, during the installation."
  LangString exanRecommended ${LANG_ENGLISH} "- recommended"
  LangString exanSkip ${LANG_ENGLISH} "Do not download now (choose a model when Exan starts)"
  LangString exanConsent ${LANG_ENGLISH} "I agree that Exan downloads the selected model from Hugging Face (huggingface.co) and stores it on this PC."
  LangString exanConsentNeeded ${LANG_ENGLISH} "Please agree to the download, or choose $\"Do not download now$\"."
  LangString exanDownloadStart ${LANG_ENGLISH} "Downloading the reading model. This can take a few minutes."
  LangString exanDownloadFailed ${LANG_ENGLISH} "The reading model could not be downloaded now. Exan will offer the download again when it starts."
  !ifdef LANG_GERMAN
    LangString exanPageTitle ${LANG_GERMAN} "Lesemodell"
    LangString exanPageSubtitle ${LANG_GERMAN} "Wähle das Modell, das die Fotos der Antwortbögen liest."
    LangString exanPageIntro ${LANG_GERMAN} "Exan liest Fotos mit einem kleinen Modell, das auf diesem PC läuft. Es ist nicht in diesem Installationsprogramm enthalten: Das gewählte Modell wird einmal während der Installation heruntergeladen."
    LangString exanRecommended ${LANG_GERMAN} "- empfohlen"
    LangString exanSkip ${LANG_GERMAN} "Jetzt nicht herunterladen (Modell beim Start von Exan wählen)"
    LangString exanConsent ${LANG_GERMAN} "Ich bin einverstanden, dass Exan das gewählte Modell von Hugging Face (huggingface.co) herunterlädt und auf diesem PC speichert."
    LangString exanConsentNeeded ${LANG_GERMAN} "Bitte stimme dem Download zu oder wähle $\"Jetzt nicht herunterladen$\"."
    LangString exanDownloadStart ${LANG_GERMAN} "Das Lesemodell wird heruntergeladen. Das kann einige Minuten dauern."
    LangString exanDownloadFailed ${LANG_GERMAN} "Das Lesemodell konnte jetzt nicht heruntergeladen werden. Exan bietet den Download beim Start erneut an."
  !endif
  !insertmacro EXAN_MODEL_LANG_STRINGS
!macroend
