export function isNearBottom(
  container: Pick<HTMLElement, "scrollHeight" | "scrollTop" | "clientHeight">,
  threshold = 72,
) {
  const distanceToBottom =
    container.scrollHeight - container.scrollTop - container.clientHeight;
  return distanceToBottom <= threshold;
}

export function scrollContainerToLatest(
  container: Pick<HTMLElement, "scrollHeight" | "scrollTo">,
  behavior: ScrollBehavior = "smooth",
) {
  container.scrollTo({
    top: container.scrollHeight,
    behavior,
  });
}
