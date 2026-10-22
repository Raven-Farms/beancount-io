/**
 * The change handler of a field that re-checks itself once it shows an error.
 *
 * Next validates the whole form with `trigger()`, which is not a submit, so
 * react-hook-form keeps its default of not re-validating a field as it is
 * edited: a currency fixed from "US" to "USD" still said "Choose a currency
 * code" until Next was pressed again (w21/238). The value is stored first, then
 * the field is re-checked, so the check sees what was just typed. A field
 * without an error is left alone and stays quiet while it is typed into.
 */
export function revalidateOnEdit<Name extends string>({
  name,
  hasError,
  trigger,
  onChange,
}: {
  name: Name;
  hasError: (name: Name) => boolean;
  trigger: (name: Name) => unknown;
  onChange: (text: string) => void;
}): (text: string) => void {
  return (text) => {
    onChange(text);
    if (hasError(name)) void trigger(name);
  };
}
