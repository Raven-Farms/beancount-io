import { de } from "../de";
import { es } from "../es";
import { nl } from "../nl";

/**
 * One form of address per locale (w21/012): German *Sie*, Dutch *je*,
 * Spanish *tú*. German Settings said "Teilen Sie …" two rows above
 * "Gefällt es dir? Hinterlasse …", which reads as unedited machine output.
 * Each pattern names the other register's pronouns and the imperatives this
 * catalog has used in it; a new string in the wrong register fails here.
 */
const strings = (catalog: Record<string, unknown>): [string, string][] =>
  Object.entries(catalog).flatMap(([key, value]) =>
    typeof value === "string"
      ? [[key, value] as [string, string]]
      : value && typeof value === "object"
        ? strings(value as Record<string, unknown>).map(
            ([k, v]) => [`${key}.${k}`, v] as [string, string],
          )
        : [],
  );

const offenders = (catalog: Record<string, unknown>, wrong: RegExp) =>
  strings(catalog)
    .filter(([, value]) => wrong.test(value))
    .map(([key]) => key);

describe("form of address", () => {
  it("addresses German users as Sie", () => {
    expect(
      offenders(
        de,
        /\b(du|Du|dein\w*|Dein\w*|dir|dich|Prüfe|Versuche|versuche|Gib|Wähle|wähle|Entdecke|Speichere|Verbinde|Verwende|Frag|Öffne|Hinterlasse|Lege)\b/u,
      ),
    ).toEqual([]);
  });

  it("addresses Dutch users as je", () => {
    expect(offenders(nl, /\b(u|U|uw|Uw)\b/u)).toEqual([]);
  });

  it("addresses Spanish users as tú", () => {
    expect(
      offenders(
        es,
        /\b(usted|Usted|ingrese|Ingrese|Agregue|Vuelva|Registre|Establezca|Explique|Añada|distinga|verifique|entienda)\b/u,
      ),
    ).toEqual([]);
  });
});
