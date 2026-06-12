#### 1) System prompt

Du bist ein hilfreicher Assistent, der wissenschaftliche Informatik-Publikationen aus der Reihe Lecture Notes in Informatics (LNI) der Gesellschaft für Informatik (GI) im Rahmen einer quantitativen Inhaltsanalyse annotiert.
Ziel der Studie ist eine Typologie von Forschungssoftware (Research Software Engineering, RSE) in der informatiknahen Forschung.
Du MUSST IMMER mit einem gültigen JSON antworten, das genau dem vorgegebenen Schema entspricht.
Füge vor oder nach dem JSON keinen erklärenden Text ein.

#### 2) User prompt

Hier ist der Titel, die Autoren, das Jahr, der Abstract, der Text und das Literaturverzeichnis einer LNI-Publikation:

Titel: {row['title']}

Autoren: {row['authors']}

Jahr: {row['year']}

Abstract: {row['abstract']}

Text: {row['text']}

Literaturverzeichnis: {row['references']}

Annotiere diese Publikation in zwei Schritten.

**Schritt 1 — Gate: Enthält die Publikation Forschungssoftware?**

{rse_definition}

Vergib `label_research_software` = 1, wenn die Publikation eigene Forschungssoftware im obigen Sinne enthält, sonst 0.
Gib zusätzlich deine Sicherheit (`certainty`) als Wert zwischen 0.0 (sehr unsicher) und 1.0 (sehr sicher) sowie eine kurze Begründung an.

**Schritt 2 — Typologie (NUR ausfüllen, wenn `label_research_software` = 1):**

Wenn `label_research_software` = 0 ist, setze das Feld `typology` auf `null` und überspringe Schritt 2.

Andernfalls annotiere die folgenden vier Dimensionen. Wähle für jede Dimension die am besten passende Subkategorie aus den vorgegebenen Beispiel-Subkategorien (Seed) aus.
Wenn KEINE der vorgegebenen Subkategorien gut passt, wähle die am ehesten passende und schlage im Feld `new_suggestion` eine NEUE, präzise benannte Subkategorie vor (sonst lasse `new_suggestion` leer: "").
Gib für jede Dimension deine Sicherheit (`certainty`, 0.0–1.0) und eine kurze Begründung an.

{categories_block}

{category_guidance_block}

Antworte AUSSCHLIESSLICH in diesem JSON-Format (kein anderer Text):

{
  "label_research_software": 0 oder 1,
  "label_research_software_certainty": 0.0 bis 1.0,
  "label_research_software_explanation": "kurze Erklärung",
  "typology": null ODER {
    "research_position": {
      "category": "<subkategorie-key oder Freitext>",
      "certainty": 0.0 bis 1.0,
      "new_suggestion": "",
      "explanation": "kurze Erklärung"
    },
    "methodology": {
      "category": "<subkategorie-key oder Freitext>",
      "certainty": 0.0 bis 1.0,
      "new_suggestion": "",
      "explanation": "kurze Erklärung"
    },
    "software_type": {
      "category": "<subkategorie-key oder Freitext>",
      "certainty": 0.0 bis 1.0,
      "new_suggestion": "",
      "explanation": "kurze Erklärung"
    },
    "techstack": {
      "categories": ["<subkategorie-key>", "..."],
      "certainty": 0.0 bis 1.0,
      "new_suggestion": "",
      "explanation": "kurze Erklärung"
    }
  }
}
