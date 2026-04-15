export async function consumeNdjsonStream<T>(
  stream: ReadableStream<Uint8Array>,
  onEvent: (event: T) => void,
  onParseError?: (rawLine: string, error: unknown) => void,
) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    let lineBreakIndex = buffer.indexOf("\n");
    while (lineBreakIndex >= 0) {
      const rawLine = buffer.slice(0, lineBreakIndex).trim();
      buffer = buffer.slice(lineBreakIndex + 1);

      if (rawLine) {
        try {
          onEvent(JSON.parse(rawLine) as T);
        } catch (error) {
          onParseError?.(rawLine, error);
        }
      }

      lineBreakIndex = buffer.indexOf("\n");
    }
  }

  const lastLine = buffer.trim();
  if (lastLine) {
    try {
      onEvent(JSON.parse(lastLine) as T);
    } catch (error) {
      onParseError?.(lastLine, error);
    }
  }
}
