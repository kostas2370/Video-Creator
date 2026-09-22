import React, { useCallback, useEffect, useState } from "react";
import { Menu, MenuButton, MenuItems } from "@headlessui/react";
import { useNavigate } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import {
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../../api/apiService";

const POLL_INTERVAL_MS = 30000;

export function NotificationBell() {
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    const response = await getNotifications();
    if (!response) return;

    setItems(response.results ?? []);
    setUnread(response.unread ?? 0);
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [load]);

  const open = async (notification) => {
    if (!notification.read) {
      setItems((prev) =>
        prev.map((item) =>
          item.id === notification.id ? { ...item, read: true } : item
        )
      );
      setUnread((count) => Math.max(0, count - 1));
      await markNotificationRead(notification.id);
    }

    if (notification.link) navigate(notification.link);
  };

  const readAll = async () => {
    setItems((prev) => prev.map((item) => ({ ...item, read: true })));
    setUnread(0);
    await markAllNotificationsRead();
  };

  const when = (value) => {
    try {
      return formatDistanceToNow(new Date(value), { addSuffix: true });
    } catch {
      return "";
    }
  };

  return (
    <Menu as="div" className="relative">
      <MenuButton
        aria-label={unread ? `${unread} unread notifications` : "Notifications"}
        className="relative rounded-full bg-gray-800 p-1 text-gray-400 hover:text-white focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-gray-800"
      >
        <span className="sr-only">View notifications</span>
        <svg
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="1.5"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
          />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </MenuButton>

      <MenuItems
        anchor="bottom end"
        className="mt-2 w-80 rounded-lg border border-gray-200 bg-white shadow-lg focus:outline-none dark:border-gray-700 dark:bg-gray-800"
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2 dark:border-gray-700">
          <span className="text-sm font-semibold text-gray-900 dark:text-white">
            Notifications
          </span>
          {unread > 0 && (
            <button
              type="button"
              className="text-xs text-blue-600 hover:underline dark:text-blue-400"
              onClick={readAll}
            >
              Mark all read
            </button>
          )}
        </div>

        {items.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
            Nothing yet. We will tell you when a video is done.
          </p>
        ) : (
          <ul className="max-h-80 overflow-y-auto">
            {items.map((notification) => (
              <li key={notification.id}>
                <button
                  type="button"
                  onClick={() => open(notification)}
                  className={`flex w-full flex-col gap-0.5 border-b border-gray-100 px-4 py-3 text-left last:border-0 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700 ${
                    notification.read ? "opacity-60" : ""
                  }`}
                >
                  <span className="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-white">
                    {!notification.read && (
                      <span className="h-2 w-2 shrink-0 rounded-full bg-blue-500" />
                    )}
                    {notification.title}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {notification.message}
                  </span>
                  <span className="text-[11px] text-gray-400">
                    {when(notification.created_at)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </MenuItems>
    </Menu>
  );
}
