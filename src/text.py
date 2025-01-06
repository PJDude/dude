#!/usr/bin/python3

####################################################################################
#
#  Copyright (c) 2023-2025 Piotr Jochymek
#
#  MIT License
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
#
####################################################################################

from locale import getlocale

class LANGUAGES:
    lang_id='en'

    STR_DICT={
        "File":{
                "pl":"Plik"},
        "Navigation":{
                "pl":"Nawigacja"},
        "Help":{
                "pl":"Pomoc"},
        "About":{
                "pl":"O programie"},
        "License":{
                "pl":"Licencja"},
        "Open current Log":{
                "pl":"Otwórz log"},
        "Open logs directory":{
                "pl":"Otwórz katalog z logami"},
        "Open homepage":{
                "pl":"Otwórz stronę domową"},
        'Find':{
                "pl":'Znajdź'},
        'Exit':{
                "pl":'Zamknij'},
        'Copy full path':{
                "pl":'Kopiuj pełną ścieżkę'},
        'Find next':{
                "pl":'Znajdź następny'},
        'Find prev':{
                "pl":'Znajdź poprzedni'},
        'Name':{
                "pl":'Nazwa'},
        'Size':{
                "pl":'Wielkość'},
        'Time':{
                "pl":'Czas'},
        'Abort':{
                "pl":'Przerwij'},
        'Ready':{
                "pl":'Gotowy'},
        'Open Folder(s)':{
                "pl":'Otwórz Folder(y)'},
        'Open File':{
                "pl":'Otwórz Plik'},
        'Open File':{
                "pl":'Otwórz Plik'},
        'Mark files':{
                "pl":'Zaznacz pliki'},
        'Unmark files':{
                "pl":'Odznacz pliki'},
        'Preview (no path)':{
                "pl":'Podgląd (brak ścieżki)'},
        "Toggle Mark":{
                "pl":'Odwróć zaznaczenie'},
        "Mark all files":{
                "pl":'Zaznacz wszystkie pliki'},
        "Unmark all files":{
                "pl":'Odznacz wszystkie pliki'},
        'Mark By expression':{
                "pl":'Zaznacz z użyciem wyrażenia'},
        'Unmark By expression':{
                "pl":'Odznacz z użyciem wyrażenia'},
        "Mark Oldest files":{
                "pl":'Zaznacz najstarsze pliki'},
        "Mark Youngest files":{
                "pl":'Zaznacz najmłodsze pliki'},
        "Unmark Oldest files":{
                "pl":'Odznacz najstarsze pliki'},
        "Unmark Youngest files":{
                "pl":'Odznacz najmłodsze pliki'},
        "Invert marks":{
                "pl":'Odwróć zaznaczenie'},
        "Toggle mark on oldest file":{
                "pl":'Odwróć zaznaczenie na najstarszym pliku'},
        "Toggle mark on youngest file":{
                "pl":'Odwróć zaznaczenie na najnowszym pliku'},
        'selecting next group':{
                "pl":'wybieranie następnego w grupie'},
        "Mark on specified directory ...":{
                "pl":'Zaznacz w wybranym katalogu ...'},
        "Unmark on specified directory ...":{
                "pl":'Odznacz z wybranego katalogu ...'},
        "Mark on scan path":{
                "pl":'Zaznacz na wybranej ścieżce skanowania'},
        "Unmark on scan path":{
                "pl":'Odznacz na wybranej ścieżce skanowania'},
        'Remove Marked Files ...':{
                "pl":'Usuń wybrane pliki'},
        'Softlink Marked Files ...':{
                "pl":'Zastąp miękkimi dowiązaniami ...'},
        'selecting next duplicate in folder':{
                "pl":'wybieranie następnego duplikatu w folderze'},
        'Create *.lnk for Marked Files ...':{
                "pl":'Utwórz pliki *.lnk z zaznaczonych plików ...'},
        'Hardlink Marked Files ...':{
                "pl":'Utwórz twarde dowiązania ...'},
        'Local (this group)':{
                "pl":'Lokalnie (wybrana grupa)'},
        'Local (this folder)':{
                "pl":'Lokalnie (wybrany folder)'},
        'All Files':{
                "pl":'Wszystkie pliki'},
        'selecting prev group':{
                "pl":'wybieranie poprzedniego w grupie'},
        'selecting prev duplicate in folder':{
                "pl":'wybieranie poprzedniego duplikatu w grupie'},
        'Path does not exist':{
                "pl":'Ścieżka nie istnieje'},
        'Abort pressed ...':{
                "pl":'Użyto "Przerwij" ... '},
        'Creating dialog ...':{
                "pl":'Tworzenie dialogu" ... '},
        'Path:':{
                "pl":'Ścieżka:'},
        'Path to scan':{
                "pl":'Ścieżka do skanowania:'},
        'Paths To scan:':{
                "pl":'Ścieżki do skanowania:'},
        'Add path to scan':{
                "pl":'Dodaj ścieżkę do skanowania'},
        'Remove path from list.':{
                "pl":'Usuń ścieżkę z listy.'},
        'Exclude from scan:':{
                "pl":'Wyklucz ze skanowania:'},
        'Add path as exclude expression ...':{
                "pl":'Dodaj ścieżkę jako wyrażenie do wykluczenia ...'},
        'Specify manually, or drag and drop here, up to 8 paths to scan':{
                "pl":'Wyspecyfikuj manualnie lub przeciągnij i upuść do 8 scieżek do skanowania'},
        'Set path to scan.':{
                "pl":'Ustaw ścieżkę do skanowania.'},
        'Select device to scan.':{
                "pl":'Wybierz ścieżkę do skanowania.'},
        'Scan':{
                "pl":'Skanuj'},
        'treat as a regular expression':{
                "pl":'traktuj jako wyrażenie regularne'},
        'Cancel':{
                "pl":'Anuluj'},
        'Operation mode':{
                "pl":'Tryb działania'},
        'TOOLTIP_CRC':{
                "en":"the classic CRC algorithm is applied\nto groups of files of the same size.",
                "pl":"klasyczny algorytm porównania CRC stosowany\ndo grup plików o tej samej wielkości"},
        'TOOLTIP_SIMILARITY':{
                "en":"Only image files are processed\nIdentified groups contain\nimages with similar content",
                "pl":"Przetwarzane są tylko pliki z grafiką\nZidentyfikowane grupy zawierają\nobrazy o podobnej treści"},
        'TOOLTIP_GPS':{
                "en":"Only image files with EXIF GPS\ndata are processed. Identified groups\ncontain images with GPS coordinates\nwith close proximity to each other",
                "pl":'Przetwarzane są tylko pliki obrazów z danymi EXIF ​​GPS.\nZidentyfikowane grupy\nzawierają obrazy z współrzędnymi GPS\nznajdującymi się blisko siebie'},
        'TOOLTIP_MIN_SIZE':{
                "en":"Limit the search pool to files with\nsize equal or greater to the specified\n (e.g. 112kB, 1MB ...)",
                "pl":'Ogranicz pulę wyszukiwania do plików o rozmiarze\n równym lub większym od określonego\n (np. 112 kB, 1 MB ...)'},
        'TOOLTIP_MAX_SIZE':{
                "en":"Limit the search pool to files with\nsize smaller or equal to the specified\n (e.g. 10MB, 1GB ...)",
                "pl":'Ogranicz pulę wyszukiwania do plików o rozmiarze\n mniejszym od lub równym określonemu\n (np. 112 kB, 1 MB ...)'},
        'TOOLTIP_HASH':{
                "en":'The larger the hash size value,\nthe more details of the image\nare taken into consideration.\nThe default value is 6',
                "pl":'Im większa wartość rozmiaru skrótu,\ntym więcej szczegółów obrazu\njest branych pod uwagę.\nWartość domyślna to 6'},
        'TOOLTIP_DIV':{
                "en":"The larger the relative divergence value,\nthe more differences are allowed for\nimages to be identified as similar.\nThe default value is 5",
                "pl":'Im większa wartość względnej rozbieżności,\ntym więcej różnic jest dozwolonych, aby\nobrazy mogły zostać zidentyfikowane jako podobne.\nWartość domyślna wynosi 5'},
        'TOOLTIP_MIN_IMAGE':{
                "en":"Limit the search pool to images with\nboth dimensions (width and height)\nequal or greater to the specified value\nin pixels (e.g. 512)",
                "pl":'Ogranicz pulę wyszukiwania do obrazów, których wymiary (szerokość i wysokość) są równe lub większe od określonej wartości nin pikseli (np. 512)'},
        'TOOLTIP_MAX_IMAGE':{
                "en":"Limit the search pool to images with\nboth dimensions (width and height)\nsmaller or equal to the specified value\nin pixels (e.g. 4096)",
                "pl":'Ogranicz pulę wyszukiwania do obrazów, których wymiary (szerokość i wysokość) są mniejsze od lub równe określonej wartości nin pikseli (np. 512)'},
        'TOOLTIP_ALL_ROTATIONS':{
                "en":"calculate hashes for all (4) image rotations\nSignificantly increases searching time\nand resources consumption.",
                "pl":'oblicz hashe dla wszystkich (4) obrotów obrazu\nZnacznie zwiększa czas wyszukiwania\ni zużycie zasobów.'},
        'TOOLTIP_SKIP':{
                "en":"log every skipped file (softlinks, hardlinks, excluded, no permissions etc.)",
                "pl":'loguj każdy pominięty plik (miękkie linki, twarde linki, wykluczone pliki, pliki bez uprawnień itd.)'},
        'Relative divergence':{
                "pl":'Relatywna rozbieżność'},
        'log skipped files':{
                "pl":'loguj pominięte pliki'},
        'Check all rotations':{
                "pl":'Analizuj warianty obrócone'},
        'Image size range (pixels)':{
                "pl":'Zakres wielkości obrazów (piksele)'},
        'Images GPS data proximity':{
                "pl":'Bliska odległość z danych GPS'},
        'Similarity mode options':{
                "pl":'Opcje trybu podobieństwa'},
        'File Mask':{
                "pl":'Maska Plików'},
        'File size range':{
                "pl":'Zakres wielkości plików'},
        'Images similarity':{
                "pl":'Podobieństwo obrazów'},
        'Parameters':{
                "pl":'Parametry'},
        'Maximum file size':{
                "pl":'Maksymalna wielkość pliku'},
        'Minimum file size.':{
                "pl":'minimalna wielkość pliku'},
        'Select Prev':{
                "pl":'Wybierz poprzedni'},
        'Select Next':{
                "pl":'Wybierz następny'},
        'Case Sensitive':{
                "pl":'Uwzględnij wiellkość znaków'},
        'Abort searching.':{
                "pl":'Przerwij szukanie.'},
        'Proceed':{
                "pl":'Kontynuuj'},
        'Close':{
                "pl":'Zamknij'},
        'Options':{
                "pl":'Opcje'},
        'Settings':{
                "pl":'Ustawienia'},
        'Show/Update Preview':{
                "pl":'Pokazuj/Aktualizuj podgląd'},
        'Hide Preview window':{
                "pl":'Ukryj okno podglądu'},
        'Remove empty folders in specified directory ...':{
                "pl":'Usuń puste foldery w wyspecyfikowanym katalogu ...'},
        'Show tooltips':{
                "pl":'Pokaż dymki z podpowiedziami'},
        'Save CSV':{
                "pl":'Zapisz CSV'},
        'Erase Cache':{
                "pl":'Wyczyść Cache'},
        'Cross paths':{
                "pl":'Różne ścieżki'},
        'Show info tooltips':{
                "pl":'Pokazuj informacyjne podpowiedzi'},
        'Show help tooltips':{
                "pl":'Pokazuj podpowiedzi z pomocą'},
        'Preview auto update':{
                "pl":'Automatyczna aktualizacja podglądu'},
        'Confirmation dialogs':{
                "pl":'Dialogi potwierdzenia'},
        'Skip groups with invalid selection':{
                "pl":'Pomiń grupy z błędną selekcją'},
        'Allow deletion of all copies':{
                "pl":'Zezwól na usunięcie wszystkich kopii'},
        'Show soft links targets':{
                "pl":'Pokazuj pliki docelowe miękkich linków'},
        'Show CRC/GROUP and size':{
                "pl":'Pokazuj CRC, grupę oraz wielkość'},
        "Processing":{
                "pl":'Przetwarzanie'},
        'No files left for processing.\nFix files selection.':{
                "pl":'Nie pozosytało plików do przetworzenia\nPopraw selekcję plików.'},
        'No Files Marked For Processing !':{
                "pl":'Nie ma zaznaczonych plików do przetworzenia !'},
        'Create relative symbolic links':{
                "pl":'Twórz miękkie dowiązania ze ścieżką względną'},
        'Erase remaining empty directories':{
                "pl":'Usuwaj pozostające puste katalogi'},
        'Abort on first error':{
                "pl":'Przerywaj przy pierwszym błędzie'},
        "Opening wrappers":{
                "pl":'Skrypty otwierające'},
        'parameters #':{
                "pl":'liczba parametrów'},
        'Folders: ':{
                "pl":'Katalogi: '},
        'Set defaults':{
                "pl":'Ustaw domyślne'},
        'TOOLTIP_PAU':{
                "en":'If enabled, any change of the selection\nwill automatically update the preview\nwindow (if the format is supported)',
                "pl":'Jeśli włączone, każda zmiana selekcji\nspowoduje automatyczną aktualizację okna podglądu\n(jeśli format jest obsługiwany)'},
        'TOOLTIP_SGWIS':{
                "en":'Groups with incorrect marks set will abort action.\nEnable this option to skip those groups.\nFor delete or soft-link action, one file in a group \nmust remain unmarked (see below). For hardlink action,\nmore than one file in a group must be marked.',
                "pl":'Grupy z niepoprawnie ustawioną selekcją przerywają przetwarzanie.\nWłącz tę opcję, aby pominąć te grupy.\nW przypadku akcji usuwania lub miękkiego linkowania jeden plik w grupie \nmusi pozostać nieoznaczony (patrz poniżej). W przypadku akcji twardego linkowania\nwięcej niż jeden plik w grupie musi być oznaczony.'},
        'TOOLTIP_ADOAC':{
                "en":'Before deleting selected files, files selection in every CRC \ngroup is checked, at least one file should remain unmarked.\nIf This option is enabled it will be possible to delete all copies',
                "pl":'Przed usunięciem wybranych plików, w każdej grupie CRC sprawdzany jest wybór plików, przynajmniej jeden plik powinien pozostać niezaznaczony.\nJeśli ta opcja jest włączona, możliwe będzie usunięcie wszystkich kopii'},
        'TOOLTIP_OW':{
                "en":'Command executed on "Open File" with full file path as parameter.\nIf empty, default os association will be executed.',
                "pl":'Polecenie wykonane na akcji „Otwórz plik” z pełną ścieżką do pliku jako parametrem.\nJeśli puste, zostanie uruchomiona domyślnie skojarzona aplikacja.'},
        'TOOLTIP_FOLDERS':{
                "en":'Command executed on "Open Folder" with full path as parameter.\nIf empty, default os filemanager will be used.',
                "pl":'Polecenie wykonane na „Otwórz folder” z pełną ścieżką jako parametrem.\nJeśli puste, zostanie użyty domyślny menedżer plików systemu operacyjnego.'},
        'TOOLTIP_FOLDERS_NUMBER':{
                "en":'Number of parameters (paths) passed to\n"Opening wrapper" (if defined) when action\nis performed on groups\ndefault is 2',
                "pl":'Liczba parametrów (ścieżek) przekazywanych do\nakcji "Skrypt Otwierający" (jeśli zdefiniowano), gdy akcja\njest wykonywana na grupach\nDomyślnie 2'},
        'TOOLTIP_ABORT':{
                "en":'If you abort at this stage,\npartial results may be available\n(if any groups are found).',
                "pl":'Jeśli przerwiesz na tym etapie,\nmogą być dostępne częściowe wyniki\n(jeśli zostaną znalezione jakiekolwiek grupy).'},

        'Go to dominant group (by size sum)':{
                "pl":'Idź do dominującej grupy (po sumarycznej wielkości)'},
        'Go to dominant group (by quantity)':{
                "pl":'Idź do dominującej grupy (po ilości)'},
        'Go to dominant folder (by size sum)':{
                "pl":'Idź do dominującego folderu (po sumarycznej wielkości)'},
        'Go to dominant folder (by quantity)':{
                "pl":'Idź do dominującego folderu (po ilości)'},
        'Go to next marked file':{
                "pl":'Idź do następnego zaznaczonego pliku'},
        'Go to previous marked file':{
                "pl":'Idź do poprzedniego zaznaczonego pliku'},
        'Go to next not marked file':{
                "pl":'Idź do następnego nie zaznaczonego pliku'},
        'Go to previous not marked file':{
                "pl":'Idź do poprzedniego nie zaznaczonego pliku'},
        'Go to next duplicate':{
                "pl":'Przejdź do następnego duplikatu'},
        'Go to previous duplicate':{
                "pl":'Przejdź do poprzedniego duplikatu'},
        'Go to first entry':{
                "pl":'Przejdź do pierwszego'},
        'Go to last entry':{
                "pl":'Przejdź do ostatniego'},
        "Mark All Duplicates in Subdirectory":{
                "pl":'Zaznacz wszystkie duplikaty w podkatalogu'},
        "Unmark All Duplicates in Subdirectory":{
                "pl":'Odznacz wszystkie duplikaty w podkatalogu'},
        'Remove Marked Files in Subdirectory Tree ...':{
                "pl":'Usuń zaznaczone pliki w poddrzewie katalogów ...'},
        'Softlink Marked Files in Subdirectory Tree ...':{
                "pl":'Usuń zaznaczone pliki w poddrzewie katalogów ...'},
        'Create *.lnk for Marked Files in Subdirectory Tree ...':{
                "pl":'Zastąp zaznaczone pliki w poddrzewie katalogów plikami *.lnk ...'},
        'Selected Subdirectory':{
                "pl":'Wybrany podkatalog'},
        'Removed empty directories':{
                "pl":'Usuniete puste katalogi'},
        'Sorting...':{
                "pl":'Sortowanie...'},
        'If you abort at this stage,\nyou will not get any results.':{
                "pl":'Jeśli przerwiesz na tym etapie,\nnie uzyskasz żadnych rezultatów.'},
        'Total space:':{
                "pl":'Całkowita przestrzeń:'},
        'Files number:':{
                "pl":'Liczba plików:'},
        'Scanning for images':{
                "pl":'Poszukiwanie obrazów'},
        'Scanning':{
                "pl":'Skanowanie'},
        'Cannot Proceed.':{
                "pl":'Nie można kontynuować.'},
        'No Duplicates.':{
                "pl":'Brak duplikatów.'},
        'Abort':{
                "pl":'Przerwij'},
        'Aborted':{
                "pl":'Przerwano'},
        'Images hashing':{
                "pl":'Hashowanie obrazów'},
        'GPS data extraction':{
                "pl":'Wydobywanie danych GPS'},
        'Starting Images hashing ...':{
                "pl":'Rozpoczęcie hashowania obrazów ...'},
        'Data clustering':{
                "pl":'Klastrowanie danych'},
        '... Clustering data ...':{
                "pl":'... Klastrowanie danych ...'},
        'Finished.':{
                "pl":'Zakończono.'},
        'Aborted.':{
                "pl":'Przerwano.'},
        '... Rendering data ...':{
                "pl":'... Wizualizacja danych ...'},
        'Rendering data...':{
                "pl":'Wizualizacja danych ...'},
        'ABORT_INFO':{
                "en":'CRC Calculation aborted.',
                "pl":'Obliczanie CRC przerwane.'},
        'ABORT_INFO_FULL':{
                "en":'\nResults are partial.\nSome files may remain unidentified as duplicates.',
                "pl":'\nWyniki są niepełne.\nNiektóre pliki mogą pozostać niezidentyfikowane jako duplikaty.'},

        'Add path ...':{
                "pl":'Dodaj ścieżkę ...'},
        'Remove expression from list.':{
                "pl":'Usuń wyrażenie z listy'},
        'Specify Exclude expression':{
                "pl":'Wyspecyfikuj wyrażenie wykluczające'},
        'expression:':{
                "pl":'wyrażenie:'},
        'Precalculating data...':{
                "pl":'Prekalkulacja danych...'},
        'GROUP/Scan Path':{
                "pl":'GRUPA/Ścieżka skanowania'},
        'GROUP':{
                "pl":'GRUPA'},
        'CRC/Scan Path':{
                "pl":'CRC/Ścieżka skanowania'},
        'Cleaning tree...':{
                "pl":'Czyszczenie drzewa'},
        'Updating items ...':{
                "pl":'Aktualizacja obiektów ...'},
        'All marked files.':{
                "pl":'Wszystkie zaznaczone pliki.'},
        'Single group.':{
                "pl":'Pojedyncza grupa.'},
        'All marked files on selected directory sub-tree.':{
                "pl":'Wszystkie zaznaczone pliki w wybranym poddrzewie katalogów'},
        'Selected Directory.':{
                "pl":'Wybrany katalog.'},

        "Opening dialog ...":{
                "pl":'Otwieranie dialogu ...'},
        'Select Directory':{
                "pl":'Wybierz katalog'},
        'Select File':{
                "pl":'Wybierz plik'},
        'All Files':{
                "pl":'Wszystkie pliki'},
        'Full path copied to clipboard':{
                "pl":'Pełna ścieżka skopiowana do schowka'},
        'Copied to clipboard:':{
                "pl":'Skopiowana do schowka:'},
        'No':{
                "pl":'Nie'},
        'Yes':{
                "pl":'Tak'},
        'Find':{
                "pl":'Znajdź'},
        'finding ...':{
                "pl":'poszukiwanie ...'},
        'No files found.':{
                "pl":'nie znaleziono plików.'},
        'Information':{
                "pl":'Informacja'},
        'Language Changed':{
                "pl":'Język został zmieniony'},
        'Restart required.':{
                "pl":'Wymagany restart aplikacji.'},
        'Language:':{
                "pl":'Język:'},
        'Opening folders(s)':{
                "pl":'Otwieranie folderó(w)'},
        'Copied to clipboard:':{
                "pl":'Skopiowano do schowka:'},
        'Scope: ':{
                "pl":'Zakres: '},
        'Mark files first.':{
                "pl":'Zaznacz najpierw pliki.'},
        'No empty subdirectories in:':{
                "pl":'Brak pustych podkatalogów w:'},
        'Confirmed.':{
                "pl":'Potwierdzono.'},
        'Hard-Link marked files together in groups ?':{
                "pl":'Utworzyć wspólne twarde dowiązania ?'},
        'replace marked files with .lnk files pointing to the first unmarked file in the group ?':{
                "pl":'zamień oznaczone pliki na pliki .lnk wskazujące na pierwszy nieoznaczony plik w grupie ?'},
        'Soft-Link marked files to the first unmarked file in the group ?':{
                "pl":'Utworzyć miekkie dowiązania z pierwszym nieoznaczonym plikiem w grupie?'},
        'Delete marked files ?':{
                "pl":'Skasować zaznaczone pliki ?'},
        "\nErase empty directories  : ":{
                "pl":"\nSkasować puste katalogi  : "},
        "\n\nSend to Trash            : ":{
                "pl":"\nPrzenieść do kosza            : "},
        "Processed files size sum : ":{
                "pl":"Suma wielkośći przetwarzanych plików : "},
        "Yes":{
                "pl":"Tak"},
        "No":{
                "pl":"Nie"},
        'Yes|RED':{
                "pl":"Tak|RED"},
        'GROUP:':{
                "pl":"GRUPA:"},
        'Link files will be created with the names of the listed files with the ".lnk" suffix.':{
                "pl":'Pliki linków zostaną utworzone z nazwami wymienionych plików z rozszerzeniem ".lnk".'},
        'Original files will be removed.':{
                "pl":'Oryginalne pliki zostaną usunięte.'},
        'confirmation required...':{
                "pl":'wymagane potwierdzenie...'},
        'remaining files checking complete.':{
                "pl":'sprawdzanie pozostającyh plików zakończone.'},
        'No action was taken.\n\nAborting. Please repeat scanning or unmark all files and groups affected by other programs.':{
                "pl":'Nie podjęto żadnej akcji.\n\nAnulowanie. Powtórz skanowanie lub usuń zaznaczenie wszystkich plików i grup, których dotyczyły inne programy.'},
        "Files on multiple devices selected.":{
                "pl":'Wybrano pliki na wielu urządzeniach.'},
        "Can't create hardlinks.":{
                "pl":'Nie można utworzyć twardych dowiązań.'},
        'final checking selection correctness':{
                "pl":'końcowe sprawdzenie popawności selekcji'},
        'Warning !':{
                "pl":'Uwaga !'},
        'Similarity mode !\nFiles in groups are not exact copies !':{
                "pl":'Tryb podobieństwa obrazów !\nPliki w grupach nie są dokładnymi kopiami !'},
        'Error. Inconsistent data.':{
                "pl":'Błąd. Niespójne dane.'},
        'Current filesystem state is inconsistent with scanned data.\n\n':{
                "pl":'Aktualny stan systemu plików jest niezgodny ze skanowanymi danymi.\n\n'},
        '\n\nSelected group will be reduced. For complete results re-scanning is recommended.':{
                "pl":'\n\nWybrana grupa zostanie zredukowana. Aby uzyskać kompletne wyniki, zaleca się ponowne zeskanowanie.'},
        'Option: \'Allow to delete all copies\' is set.|RED\n\nAll copies may be selected.|RED\n\nProceed ?|RED':{
                "pl":'Opcja: \'Zezwól na usunięcie wszystkich kopii\' jest włączona.|RED\n\nMożna wybrać wszystkie kopie.|RED\n\nKontynuować?|RED'},
        'Option \"Skip groups with invalid selection\" is enabled.\n\nFollowing groups will NOT be processed and remain with markings:':{
                "pl":'Opcja "Pomiń grupy z błędną selekcją" jest włączona.\n\nNastępujące grupy NIE zostaną przetworzone i pozostaną z zaznaczeniami:'},
        "Keep at least one file unmarked\nor enable option:\n\"Skip groups with invalid selection\"\nor enable option:\n\"Allow deletion of all copies\"":{
                "pl":'Zachowaj przynajmniej jeden plik nieoznaczony\nlub włącz opcję:\n"Pomiń grupy z błędną selekcją"\nlub włącz opcję:\n"Zezwól na usuwanie wszystkich kopii"'},
        "Keep at least one file unmarked\nor enable option:\n\"Skip groups with invalid selection\"":{
                "pl":"Zachowaj przynajmniej jeden plik nieoznaczony\lub włącz opcję:\n\"Pomiń grupy z błędną selekcją\""},
        "Option \"Skip groups with invalid selection\" is enabled.\n\nFollowing groups will NOT be processed and remain with markings:\n\n":{
                "pl":"Opcja \"Pomiń grupy z błędną selekcją\" jest włączona.\n\nNastępujące grupy NIE zostaną przetworzone i pozostaną z oznaczeniami:\n\n"},
        'All files marked':{
                "pl":'Wszystkie pliki są zaznaczone'},
        'Single file marked':{
                "pl":'Pojedynczy plik zaznaczony'},
        "Mark more files\nor enable option:\n\"Skip groups with invalid selection\"":{
                "pl":"Zaznacz więcej plików\nlub włącz opcję:\n\"Pomiń grupy z błędną selekcją\""},
        'checking selection correctness...':{
                "pl":'sprawdzanie poprawności seleckji...'},
        'checking data consistency with filesystem state ...':{
                "pl":'sprawdzanie spójności danych ze stanem systemu plików'},

        'Results display mode':{
                "pl":'Tryb wyświetlania wyników'},
        'Scope: All groups.':{
                "pl":'Zakres: Wszystkie grupy.'},
        'Scope: Selected directory.':{
                "pl":'Zakres: Wybrany katalog.'},
        'All (default)':{
                "pl":'Wszystkie (domyślnie)'},
        'TOOLTIP_CP':{
                "en":'Ignore (hide) groups containing duplicates in only one search path.\nShow only groups with files in different search paths.\nIn this mode, you can treat one search path as a "reference"\nand delete duplicates in all other paths with ease',
                "pl":'Ignoruj ​​(ukryj) grupy zawierające duplikaty tylko w jednej ścieżce wyszukiwania.\nPokaż tylko grupy zawierające pliki w różnych ścieżkach wyszukiwania.\nW tym trybie możesz traktować jedną ścieżkę wyszukiwania jako "referencje"\ni z łatwością usuwać duplikaty we wszystkich innych ścieżkach.'},
        'Show all results':{
                "pl":'Pokaż wszystkie wyniki'},
        'TOOLTIP_SD':{
                "en":'Show only groups with result files in the same directory',
                "pl":'Pokaż tylko grupy z plikami wyników w tym samym katalogu'},
        'Same directory':{
                "pl":'Ten sam katalog'},
        "Main panels and dialogs":{
                "pl":'Panele główne i dialogi'},
        'Show full CRC':{
                "pl":'Pokazuj pełne CRC'},
        'TOOLTIP_SFC':{
                "en":'If disabled, shortest necessary prefix of full CRC wil be shown',
                "pl":'Jeśli wyłączone, zostanie wyświetlony najkrótszy niezbędny prefiks pełnego CRC'},
        ' Search:':{
                "pl":' Szukaj:'}
    }

    def __init__(self):
        try:
            lang = getlocale()[0].split('_')[0]
            #print(f'initial setting lang:{lang}')
        except:
            pass

    def set(self,lang_id):
        #print(f'setting lang:{lang_id}')
        self.lang_id=lang_id

    def STR(self,str_par):
        try:
            return self.STR_DICT[str_par][self.lang_id]
        except:
            try:
                return self.STR_DICT[str_par]["en"]
            except:
                return str_par
