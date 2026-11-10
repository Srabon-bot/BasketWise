"use client";

import { useId, useMemo, useState } from "react";

type Props = {
  items: string[];
  onSelect: (item: string) => void;
  label: string;
  placeholder?: string;
  initialValue?: string;
  clearOnSelect?: boolean;
};

export function ItemCombobox({
  items,
  onSelect,
  label,
  placeholder = "Start typing an item",
  initialValue = "",
  clearOnSelect = false,
}: Props) {
  const listId = useId();
  const [query, setQuery] = useState(initialValue);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return items.slice(0, 8);

    return items
      .filter((item) => item.includes(needle))
      .sort((a, b) => {
        const aStarts = a.startsWith(needle) ? 0 : 1;
        const bStarts = b.startsWith(needle) ? 0 : 1;
        return aStarts - bStarts || a.localeCompare(b);
      })
      .slice(0, 8);
  }, [items, query]);

  const exact = items.find(
    (item) => item.toLowerCase() === query.trim().toLowerCase(),
  );

  function choose(item: string) {
    onSelect(item);
    setQuery(clearOnSelect ? "" : item);
    setOpen(false);
    setActive(0);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActive((value) => Math.min(value + 1, filtered.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      setActive((value) => Math.max(value - 1, 0));
    } else if (event.key === "Enter") {
      if (open && filtered[active]) {
        event.preventDefault();
        choose(filtered[active]);
      }
    } else if (event.key === "Escape") {
      setOpen(false);
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  }

  return (
    <div className="field">
      <label htmlFor={`${listId}-input`}>{label}</label>
      <div className="combobox">
        <input
          id={`${listId}-input`}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={
            open && filtered[active] ? `${listId}-option-${active}` : undefined
          }
          autoComplete="off"
          placeholder={placeholder}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
            setActive(0);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={onKeyDown}
        />
        {open ? (
          <ul className="combobox-list" id={listId} role="listbox">
            {filtered.length === 0 ? (
              <li className="combobox-empty" role="presentation">
                No item matches “{query.trim()}”.
              </li>
            ) : (
              filtered.map((item, index) => (
                <li
                  key={item}
                  id={`${listId}-option-${index}`}
                  className="combobox-option"
                  role="option"
                  aria-selected={index === active}
                  onMouseDown={(event) => {
                    event.preventDefault();
                    choose(item);
                  }}
                  onMouseEnter={() => setActive(index)}
                >
                  {item}
                </li>
              ))
            )}
          </ul>
        ) : null}
      </div>
      <p className="field-help">
        {exact
          ? `${exact} is selected. Type to choose another item.`
          : query.trim()
            ? `${filtered.length} match${filtered.length === 1 ? "" : "es"} shown. Use the arrow keys and Enter.`
            : `${items.length} items have recommendations. Use the arrow keys and Enter.`}
      </p>
    </div>
  );
}
