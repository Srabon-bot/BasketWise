"use client";

import { useCallback, useEffect, useState } from "react";

type JsonState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
};

type Payload<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

/**
 * Small typed loader for the static JSON exports in /public/data.
 * Loading, error and retry are part of the contract so no page can ship
 * a silent blank state.
 */
export function useJson<T>(url: string): JsonState<T> {
  const [payload, setPayload] = useState<Payload<T>>({
    data: null,
    loading: true,
    error: null,
  });
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => {
    setPayload({ data: null, loading: true, error: null });
    setAttempt((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    fetch(url, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`The file ${url} answered ${response.status}.`);
        }
        return response.json() as Promise<T>;
      })
      .then((data) => {
        setPayload({ data, loading: false, error: null });
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") {
          return;
        }
        setPayload({
          data: null,
          loading: false,
          error:
            reason instanceof Error
              ? reason.message
              : "The data file could not be loaded.",
        });
      });

    return () => controller.abort();
  }, [url, attempt]);

  return { ...payload, retry };
}
