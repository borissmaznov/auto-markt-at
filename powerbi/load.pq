// Power Query (M): lädt die vier CSV-Tabellen direkt aus dem GitHub-Repository.
// In Power BI Desktop: Daten abrufen -> Leere Abfrage -> Erweiterter Editor -> diesen Text einfügen.
// Für jede Tabelle eine eigene Abfrage anlegen und den Namen in der letzten Zeile anpassen
// ("fact_registrations", "dim_make", "dim_year", "dim_drive").
let
    Basis = "https://raw.githubusercontent.com/borissmaznov/auto-markt-at/main/powerbi/data/",
    Laden = (name as text) as table =>
        let
            Roh = Csv.Document(Web.Contents(Basis & name & ".csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
            MitKopf = Table.PromoteHeaders(Roh, [PromoteAllScalars = true])
        in
            MitKopf,
    Typen = [
        fact_registrations = {{"year", Int64.Type}, {"make", type text}, {"model", type text}, {"drive", type text},
                              {"fuel", type text}, {"regs", Int64.Type}, {"co2_g_km", type number},
                              {"power_kw", type number}, {"mass_kg", type number}, {"consumption_wh_km", type number}},
        dim_make = {{"make", type text}, {"brand", type text}, {"focus_brand", Int64.Type}},
        dim_year = {{"year", Int64.Type}, {"label", type text}, {"provisional", Int64.Type}},
        dim_drive = {{"drive", type text}, {"label", type text}, {"sort", Int64.Type}}
    ],
    Tabelle = "fact_registrations",
    Ergebnis = Table.TransformColumnTypes(Laden(Tabelle), Record.Field(Typen, Tabelle), "en-US")
in
    Ergebnis
