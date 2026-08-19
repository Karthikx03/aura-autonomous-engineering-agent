"use client";

import { useEffect, useRef, useState } from "react";
import { type AgentEvent, getTaskWsUrl } from "./api";

export type SocketStatus = "connecting" | "open" | "closed" | "error";

/**
 * Opens a WebSocket to /ws/tasks/{taskId} and accumulates AgentEvent
 * messages as they stream in. Degrades gracefully: if the connection
 * fails or the backend is unreachable, it never throws, it just reports
 * status "error"/"closed" and leaves events as whatever was received.
 */
export function useTaskSocket(taskId: string | null | undefined): {
  events: AgentEvent[];
  status: SocketStatus;
} {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [status, setStatus] = useState<SocketStatus>(() => (taskId ? "connecting" : "closed"));
  const socketRef = useRef<WebSocket | null>(null);

  // Reset local state synchronously during render when the task id changes,
  // rather than via a setState call at the top of the effect (avoids an
  // extra cascading render and keeps the effect focused on the subscription
  // itself, per https://react.dev/learn/you-might-not-need-an-effect).
  const [trackedTaskId, setTrackedTaskId] = useState(taskId);
  if (taskId !== trackedTaskId) {
    setTrackedTaskId(taskId);
    setEvents([]);
    setStatus(taskId ? "connecting" : "closed");
  }

  useEffect(() => {
    if (!taskId) return;

    let cancelled = false;
    let socket: WebSocket | null = null;

    try {
      socket = new WebSocket(getTaskWsUrl(taskId));
      socketRef.current = socket;

      socket.onopen = () => {
        if (!cancelled) setStatus("open");
      };

      socket.onmessage = (evt) => {
        if (cancelled) return;
        try {
          const parsed = JSON.parse(evt.data) as AgentEvent;
          setEvents((prev) => [...prev, parsed]);
        } catch {
          // ignore malformed frames rather than crashing the UI
        }
      };

      socket.onerror = () => {
        if (!cancelled) setStatus("error");
      };

      socket.onclose = () => {
        if (!cancelled) setStatus((prev) => (prev === "error" ? prev : "closed"));
      };
    } catch {
      // Constructing the WebSocket synchronously threw (e.g. malformed URL).
      // Report it asynchronously so this stays a subscription callback
      // rather than a direct setState call in the effect body.
      queueMicrotask(() => {
        if (!cancelled) setStatus("error");
      });
    }

    return () => {
      cancelled = true;
      try {
        socket?.close();
      } catch {
        // ignore
      }
      socketRef.current = null;
    };
  }, [taskId]);

  return { events, status };
}
