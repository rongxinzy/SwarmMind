// Environment configuration
export const env = {
  API_URL:
    // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
    typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL
      ? process.env.NEXT_PUBLIC_API_URL
      : "http://localhost:8000",
  NEXT_PUBLIC_STATIC_WEBSITE_ONLY: false,
};
