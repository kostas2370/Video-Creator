import { toast } from "react-toastify";
import { axiosPrivateInstance } from "./axiosPrivate";

export function errorMessage(error) {
  const data = error?.response?.data;
  if (!data) return "The server could not be reached";
  if (typeof data === "string") {
    if (/^\s*(?:<!doctype\s+html|<html\b)/i.test(data)) {
      return error.response.status === 404
        ? "This feature is unavailable on the server. Please refresh and try again."
        : "The server could not complete the request. Please try again.";
    }
    return data;
  }
  const first = value => {
    if (Array.isArray(value)) return first(value[0]);
    if (value && typeof value === "object") {
      const [field, detail] = Object.entries(value)[0] || [];
      if (!field) return "The request was refused";
      const message = first(detail);
      return ["detail", "message", "non_field_errors"].includes(field) ? message : `${field}: ${message}`;
    }
    return String(value ?? "The request was refused");
  };
  return first(data);
}

// All API helpers resolve the same result. HTTP errors never masquerade as data.
export async function request({ method = "get", url, data, params, responseType, client = axiosPrivateInstance, notifyError = true }) {
  try {
    const response = await client.request({ method, url, data, params, ...(responseType ? { responseType } : {}) });
    return { ok: true, data: response.data ?? null, status: response.status, headers: response.headers, message: null, errors: null };
  } catch (error) {
    if (typeof Blob !== "undefined" && error?.response?.data instanceof Blob) {
      try {
        const body = await error.response.data.text();
        try { error.response.data = JSON.parse(body); }
        catch { error.response.data = body; }
      } catch { /* Use the standard error message if the body cannot be read. */ }
    }
    const message = errorMessage(error);
    if (notifyError) toast.error(message, { toastId: `${method}:${url}:${message}` });
    return { ok: false, data: null, status: error?.response?.status ?? null, headers: error?.response?.headers ?? {}, message, errors: error?.response?.data ?? null };
  }
}
