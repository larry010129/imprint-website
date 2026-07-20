import { useCallback, useState, type ChangeEvent } from "react";

export function useCharacterLimit({
  maxLength,
  initialValue = "",
}: {
  maxLength: number;
  initialValue?: string;
}) {
  const [value, setValue] = useState(() =>
    initialValue.length > maxLength ? initialValue.slice(0, maxLength) : initialValue,
  );

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => {
      const next = e.target.value;
      setValue(next.length > maxLength ? next.slice(0, maxLength) : next);
    },
    [maxLength],
  );

  return {
    value,
    setValue,
    characterCount: value.length,
    handleChange,
    maxLength,
  };
}
