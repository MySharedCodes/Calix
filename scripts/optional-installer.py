"""Add true NSIS optional sections to Tauri's generated installer."""
from pathlib import Path
import json
import re
import subprocess

root=Path(__file__).resolve().parents[1]
subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(root/'scripts/installer-brand.ps1')], check=True)
directory=root/'src-tauri/target/release/nsis/x64'
original=(directory/'installer.nsi').read_text(encoding='utf-8')
version=json.loads((root/'package.json').read_text())['version']
output=root/f'release/Calix_{version}_x64-setup.exe'
text=original.replace('!define OUTFILE "nsis-output.exe"',f'!define OUTFILE "{output}"')
text=text.replace('"Calix Notebook"','"Calix.Notebook"')
# Use a stable ProgID and quote both paths, including installations with spaces.
text=text.replace(r'"$INSTDIR\${MAINBINARYNAME}.exe $\"%1$\""',
                  r'"$\"$INSTDIR\${MAINBINARYNAME}.exe$\" $\"%1$\""')
text=text.replace('  ; Register deep links','  !insertmacro UPDATEFILEASSOC\n  ; Register deep links')
text=text.replace('!insertmacro MUI_PAGE_DIRECTORY','!insertmacro MUI_PAGE_COMPONENTS\n!insertmacro MUI_PAGE_DIRECTORY')
text=text.replace('Section Install','Section "Calix Core (required)"\n  SectionIn RO',1)
text=text.replace('Function .onInit','Function .onInit\n  Call CalixSelectComponents',1)
text=text.replace('Section Uninstall','Section Uninstall\n  RMDir /r "$INSTDIR\\components"',1)
text += r'''

Section "PDE module" SEC_PDE
  SetOutPath "$INSTDIR\components\pde"
  File /r "@@COMPONENTS@@\pde\*"
SectionEnd
Section "Additional languages (JA / FR / RU / DE / ES)" SEC_LANGUAGES
  SetOutPath "$INSTDIR\components"
  File "@@COMPONENTS@@\languages.json"
SectionEnd
Section "Themes (Black / Pink / Ocean / Forest)" SEC_THEMES
  SetOutPath "$INSTDIR\components"
  File "@@COMPONENTS@@\themes.css"
SectionEnd

Section -CalixComponentManifest
  ${IfNot} ${SectionIsSelected} ${SEC_PDE}
    RMDir /r "$INSTDIR\components\pde"
    WriteRegDWORD HKCU "Software\calix\Calix\Components" "PDE" 0
  ${Else}
    WriteRegDWORD HKCU "Software\calix\Calix\Components" "PDE" 1
  ${EndIf}
  ${IfNot} ${SectionIsSelected} ${SEC_LANGUAGES}
    Delete "$INSTDIR\components\languages.json"
    WriteRegDWORD HKCU "Software\calix\Calix\Components" "LANGUAGES" 0
  ${Else}
    WriteRegDWORD HKCU "Software\calix\Calix\Components" "LANGUAGES" 1
  ${EndIf}
  ${IfNot} ${SectionIsSelected} ${SEC_THEMES}
    Delete "$INSTDIR\components\themes.css"
    WriteRegDWORD HKCU "Software\calix\Calix\Components" "THEMES" 0
  ${Else}
    WriteRegDWORD HKCU "Software\calix\Calix\Components" "THEMES" 1
  ${EndIf}
SectionEnd

Function CalixSelectComponents
@@SELECTIONS@@
FunctionEnd
'''.replace('@@COMPONENTS@@',str(root/'release/components'))
selection=[]
for component in ('PDE','LANGUAGES','THEMES'):
    selection.append(r'''
  ClearErrors
  ReadRegDWORD $R8 HKCU "Software\calix\Calix\Components" "@@NAME@@"
  ${IfNot} ${Errors}
    ${If} $R8 == 0
      !insertmacro UnselectSection ${SEC_@@NAME@@}
    ${EndIf}
  ${EndIf}
  ClearErrors
  ${GetOptions} $CMDLINE "/@@NAME@@=" $R8
  ${IfNot} ${Errors}
    ${If} $R8 == "0"
      !insertmacro UnselectSection ${SEC_@@NAME@@}
    ${ElseIf} $R8 == "1"
      !insertmacro SelectSection ${SEC_@@NAME@@}
    ${EndIf}
  ${EndIf}
'''.replace('@@NAME@@',component))
text=text.replace('@@SELECTIONS@@',''.join(selection))
text=text.replace('!include MUI2.nsh','!include MUI2.nsh\n!include Sections.nsh')
art=root/'src-tauri/installer-assets'
branding='\n'.join([
    '!define MUI_WELCOMEFINISHPAGE_BITMAP "'+str(art/'welcome.bmp')+'"',
    '!define MUI_HEADERIMAGE',
    '!define MUI_HEADERIMAGE_BITMAP "'+str(art/'header.bmp')+'"',
    '!define MUI_HEADERIMAGE_RIGHT',
    '!define MUI_WELCOMEPAGE_TITLE "Calix"',
    '!define MUI_WELCOMEPAGE_TEXT "Calculation && Interactive Xpressions$\\r$\\n$\\r$\\n$(MUI_TEXT_WELCOME_INFO_TEXT)"',
])
# Preserve Tauri's language-specific welcome text and install-mode handling.
text=text.replace('!insertmacro MUI_PAGE_WELCOME',branding+'\n!insertmacro MUI_PAGE_WELCOME',1)
target=directory/'calix-components.nsi'
text+='\nLangString older ${LANG_GERMAN} "aelter"\nLangString unknown ${LANG_GERMAN} "unbekannt"\n'
target.write_text(text,encoding='utf-8')
compiler=Path.home()/'AppData/Local/tauri/NSIS/makensis.exe'
if not compiler.exists():compiler=root/'tools/nsis-unpacked/nsis-3.08/Bin/makensis.exe'
subprocess.run([str(compiler),'/V2',str(target)],cwd=directory,check=True)
# stage-release consumes the conventional Tauri bundle path.
import shutil
shutil.copy2(output,root/f'src-tauri/target/release/bundle/nsis/Calix_{version}_x64-setup.exe')
print('Built component-selectable installer:',output)
