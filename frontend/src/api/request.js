import { toast } from "react-toastify";
import { axiosPrivateInstance } from "./axiosPrivate";

export function errorMessage(error) {
  const data = error?.response?.data;
  if (!data) return "The server could not be reached";
  if (typeof data === "string") return data;
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
export async function request({ method = "get", url, data, params, client = axiosPrivateInstance, notifyError = true }) {
  try {
    const response = await client.request({ method, url, data, params });
    return { ok: true, data: response.data ?? null, status: response.status, headers: response.headers, message: null, errors: null };
  } catch (error) {
    const message = errorMessage(error);
    if (notifyError) toast.error(message, { toastId: `${method}:${url}:${message}` });
    return { ok: false, data: null, status: error?.response?.status ?? null, headers: error?.response?.headers ?? {}, message, errors: error?.response?.data ?? null };
  }
}
