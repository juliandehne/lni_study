# Feedback Category Schema

__Feedback zum Schema vom 30.07.2026__

Mein Mentales Model von dem Prozess basierend auf deinen Erzählungen beim
Mittagessen und der Dokumentation am Anfang von `category_schema.yaml`. Ich habe
Dokumentation bis Zeile 27 mir von der RWTH LLM zusammenfassen lassen. Ich gehe
davon aus, dass das ist, wenn die Daten sowieso öffentlich sind.

## Verständnis / Frage LLM-Methodik

### Iterativer Narrowing-Prozess

```
Wiederhole:

    Modell annotiert Daten mit vorhandenen Kategorien
    Modell schlägt ggf. neue Kategorien vor

    Sammle neue Vorschläge in candidates

    Mensch reviewed candidates:

        Wenn sinnvoll:
            verschiebe nach active
            ergänze description

        Wenn nicht sinnvoll:
            verschiebe nach rejected
            ergänze reason

        Wenn Duplikat/Synonym:
            merge in bestehende active-Kategorie
            ergänze examples

Bis keine relevanten neuen candidates mehr auftreten
```

Was ist die Abbruchsbedingung von `Wiederhole` bei der Studie?

> Modell annotiert Daten mit vorhandenen Kategorien

Ich schätze mal, ihr gebt der LLM jeweils ein Paper einzeln jeweils mit der
Definition `definition_de` um die Attention hochzuhalten.

~Falls ihr das noch nicht macht (und es noch in der Zeit sinnvoll umsetzbar ist)
könnt ihr die LLM bitten ihre Einschätzungen pro Kategorie mit Verweis auf das
Dokument (eine Textstelle) zu begründen.~
Ok steht in den rationales.

### Prompt Erstellen

```
Lade category_schema.yaml

Für jede Dimension im Schema:

    prompt_kategorien = []

    Für jede Kategorie in active:

        Wenn deprecated == true:
            Behalte Kategorie als bekannten Altwert
            Überspringe sie für den Prompt

        Sonst wenn description leer ist:
            Gib Warnung aus
            Überspringe sie für den Prompt

        Sonst:
            Füge Kategorie mit description zum Prompt hinzu

            Wenn examples vorhanden:
                Füge examples als Synonyme hinzu

    Für jede Kategorie in rejected:
        Füge sie als "nicht verwenden" zum Prompt hinzu
        Falls move_to vorhanden:
            Verweise auf Zielkategorie

    candidates bleiben unverändert gespeichert
    und werden erst durch Review entschieden

Generiere daraus den Annotation-Prompt
```

> Die bloße Anwendung allgemein verfügbarer Standardsoftware ohne eigene
> Entwicklungsleistung gilt NICHT als Forschungssoftware.

Mein Stand von vor einem 3/4 Jahr war, dass LLM Modelle manchmal das NICHT
"vergessen". Vermutlich ist das inzwischen besser geworden. Falls ihr beim
Reviewen denkt, etwas fällt in die "nicht"-Kategorie könntet ihr Formulierungen
mit "keine" verwenden.

> Entscheidend ist, dass die Software im Rahmen der beschriebenen Arbeit
> tatsächlich umgesetzt (erstellt, erweitert oder angepasst) wurde.

Das ist eine gute Einschränkung.

In welchen Sprachen sind die Paper? Für die kognitive Last wäre es besser, wenn
das Modell nicht zwischen Sprachen (und Übersetzungen von Fachbegriffen)
wechseln muss. Wenn Beispielsweise die Paper sowohl auf Deutsch als auch auf
Englisch sind, kann ein Promptzusatz (Kontext auf Englisch, Antworte auf
Deutsch, Nutze Fachbegriffe unverändert) sinnvoll sein. Entsprechend würde ich
die prompt einheitlich auf einer Sprache machen.

## Feedback Kategoriensystem

Je nachdem wie du über die Kategorien reporten möchtest, würde ich sie so schön
schreiben, dass du sie 1:1 automatisch exportieren kannst. Dann hättest du eine
SSOT.

### Research Position

Die Position im Forschungsablauf ist etwas trügerisch. Ich kann eine
Datenanalyse sowohl am Anfang machen um darauf aufbauend etwas zu erforschen
oder am Ende. Wie wäre es mit "Research Purpose"

#### Datenerhebung

> Datenerhebung / data acquisition (Sensorik, Crawler, Logging,
> Erhebungsinstrumente).

Sensoren, (Web-)Crawler, Logging, Erhebungsinstrumente sind vom Softwaredesign
(typische Programmiersprachen, Komplexität, Low-Level-Code (Sensoren) vs.
OO-Code (Crawler)) sehr unterschiedlich.

#### Formale Verification

Wenn du der LLM konkrete Aufzählungen / Beispiele für eine Kategorie gibst,
bringt das mehr Attention auf den Begriff und sorgt (theoretisch) dafür, dass
die Zuweisung genauer wird. Oder anders gesagt, auch wenn LLMs wissen das
SAT-Solver für formale Verifikation genutzt werden, könnte diese Information
(zu) tief im Modell "vergraben" liegen und nicht aktiviert werden. Durch immer
bessere Modelle sollte dieser Effekt geringer werden. Bei Experimenten mit
OpenAI's o3 mit Begriffen aus der Physik haben wir den Effekt noch spürbar
beobachten können.

Außerdem ist so die Beschreibung einheitlicher und es hilft den Menschen.

> description: formale Verifikation oder Beweisführung ist eine spezielle Form
> von RSE und folgt daher auch eingem eignen Process und damit auch eine eigene
> (neue) Position

> description: formale Verifikation oder Beweisführung (Theorembeweiser,
> Beweisassistenten, Modellprüfungssoftware, SMT-Solver, SAT-Solver,
> Spezifikations- und Verifikationswerkzeuge, Programmanalyse-Software)

#### research_infrastructure_support

Hiermit wäre beispielsweise eine elektronisches Laborbuch gemeint, oder? Das
würde sich etwas mit "Entwicklungsinfrastruktur" beißen.

> da die Position im Forschungsprozess die Bereitstellung einer
> Entwicklungsinfrastruktur

#### product_result

Ich frage mich, ob der eigentliche Unterschied zwischen
`proof_of_concept_product` und `product_result` nicht einfach im (angestrebten)
Reifegrad oder Umfang und damit in einer anderen Dimension liegt.

`proof_of_concept_product`: TRL 3-4
`product_result`: TRL 5- (6?)

Wenn die Definition so umfangreich/ verschachtelt ist, ist das für mich ein
Smell, dass sie konzeptuell falsch ist.

Falls du es doch behalten möchtest: Ich würde erst `proof_of_concept_product`
nennen, da Referenzen auf Inhalt der Bereits im Kontext ist vermutlich von LLMs
einfacher verstanden werden.

#### research_infrastructure_management

```
- key: research_infrastructure_management
  reason: research infrastructure software fällt nicht unter die engere
  Definition von Forschungssoftware als Teil eines konkreten Forschungsprozesses
```

Widerspricht sich das nicht mit `research_infrastructure_support` (Oder mein
Verstädnis vom letzten ist falsch)

### software_lifecycle

/

### software_type

Vermischt das zwei Dimensionen?

1. Wie wird die Software ausgeliefert? (library_package, full_stack_application,
   plugin_extension)
2. Welchen Zweck erfüllt die Software? Unser Emeritus Prof vertritt die Meinung,
   dass Software Architekturen in eine diese drei Kategorien eingeteilt werden
   können. Und zu mindest auf Architekturebene konnte ich die letzten Jahre
   keine Gegenbeispiele finden.
   * Datentransformationspipelines (analysis_pipeline, numerical_mathematical,
     Language Workbenches (siehe Anmerkung zu DSL), ml_model (habe etwas
     Bauschmerzen bei der Einteilung))
   * Eingebettetes System (also physisische Maschinensteuern, Sensordaten
     aufnehmen) (embedded_hardware)
   * Interaktives System (middleware_service, vr_application)

* domain_specific_language: DSLs sind in Verbindung mit Language Workbenches ein
  Metatool (Datentransformationspipeline), dass (Teil-)Systeme aus 2. erstellen
  kann. Alternativ können DSLs als Frontend, Middleware, oder Backend in allen
  Systemen aus 2. eingesetzt werden.

* Wie geht ihr mit hierarchischen Kategorien um?
   * Ggf. können 2. auch erstmal in die existierenden Kategorien einordnen
     lassen und die drei ober Kategorien im Paper darstellen.

Ich habe die rejected nur überflogen.

__Feedback zum Schema vom 02.08.2026, ab Zeile 426__

### techstack

> Das ist KEINE Spekulation und darf kodiert werden

Ich würde erwarten, dass es kodiert werden "muss" oder "soll". Worauf sich "Das"
bezieht, ist nicht ganz eindeutig.

> ein Paper, das ausschließlich Verfahren benennt, ist
> `insufficient_information`

Für spätere Statistiken wäre es eigentlich besser unterscheiden zu können welche
Paper nur Verfahren benennen und welche Paper über die Implementierung sprechen
die LLM aber nicht in der Lage ist den Techstack zu erfahren. Kann mir aber auch
gut vorstellen, dass viele Paper in "Ohne Implementierung" einkategorisiert,
weil die Autoren zu wenig darüber geschrieben haben.

### Evaluation der Forschungssoftware

Sehr sehr gute Kategorie. Ich bin immer noch der Meinung, dass wir als Diziplin
mehr dafür tun müssen Software ordentlich zu evaluieren.

> empirical_study

Hier würde ich zwischen Studien mit Menschen und rechnerischen Experimenten
unterscheiden, da es methodisch sehr anders ist und auch andere Arten von Fragen
beantwortet werden können.

* research position (Anwendungszweck der Software)
* software lifecycle (Projektphase der Software, die im Paper beschrieben wird)
* software type (Bereitstellung der Software vs. Architektur der Software)
* techstack (Verwendete Technologien)
* evaluation (Evaluation der Software)
* Neue Vorschläge:
   * Lizenzmodell
   * Disziplin (auch wenn es sich um hauptsächlich Informatik Paper handelt,
     könnten wir uns das nochmal bestätigen lassen)
   * Zielgruppe (Forschende, Öffentlichkeit, Lehre)
   * Verwendung/ Abgrenzung zu Standards (daraus lässt sich bestimmt etwas für
     den Transfer in die Industrie / Wiederverwendbarkeit ableiten)

Meine Physiker haben selbstständig dig ein Kategoriensystem für ihre Software
entwickelt. Interessanterweise ist das orthogonal zu diesem. Bei denen geht es
eher um "Zielgruppe", "Größe", "Use Case", "Voraussichtliche Nutzungsdauer" um
daraus die benötigte/ angestrebte Qualität / geeignete Softwaremethoden (testen
ja/nein, sinnvolle Datenstrukturen ja/nein) ableiten zu können. Das liegt aber
an präskriptiv (dieses) vs. deskriptiv (deren) Kategoriensystem.

Weitere Fragen/Gedanken (zum Einsatz von LLMs):

Disclaimer:

1. Ich habe mir den Quellcode noch nicht angeschaut.
2. Mir ist bewusst, dass ihr auf viele Sachen vermutlich bereits selbst gekommen
   seid.
3. Mir ist bewusst, dass wir nicht beliebig viel Zeit haben. Also priorisiert
   und lehnt die Vorschläge gerne ab.

* Wie viele Paper analysiert ihr insgesamt?
* Welche LLMs nutzt ihr?
* Wir können ein Majority Voting machen. Entweder 2 LLMs, bei ungleichen
  Meinungen entscheidet ein Coder oder 3 LLMs. Vielleicht hat mir Julian das
  aber schon mal beim Mittagessen gepitch und ihr macht es schon so.
* Wurden 100 Paper von Menschen händisch ohne LLM Unterstützung analysiert oder
  wurde für 100 Paper die LLM ausgeführt und bei "Unsicherheiten" z.B.
  Candidates das Codesystem angepasst?
* Bei Evaluationen/ Überprüfung von LLMs fahren ein Kollege und ich den Ansatz,
  dass wir die Menge der evaluierten Artefakte nicht am Anfang festsetzen (n=100
  hier), sondern die Stabilität der Ergebnisse einfließen lassen. In dem Fall in
  etwa: Solange händisch nachjustieren bis über X-Paper keine ernsthaften neuen
  Kategorien gefunden wurden. Ich schätze mal, ihr habt das implizit in n=100
  bereits enthalten.
* Habt ihr euch über die Evaluation bereits Gedanken gemacht? Wir könnten die
  Zuverlässigkeit der Kategorisierung prüfen, indem synonyme Paper/ Tools gleich
  kategorisiert werden (z.B. aufeinander aufbauende Paper zu einem Tool) und
  ähnliche Tools mit dem gleichen zweck/ Technologien ebenfalls richtig
  einsortiert werden.
* Zwei Möglichkeiten der LLM noch mehr Fokus auf die Kategorisierung zu geben:
   1. Paper als reinen Text zu geben, also vorher zu konvertieren.
      Möglicherweise verwenden LLM anbieten bereits intern tools wie
      marker/markitdown. Es könnte uns Token sparen, fall es relevant ist und
      wir hätten mehr Kontrolle über die Inputqualität.
   2. Wir lassen jede Dimension einzeln pro Anfrage beantworten.