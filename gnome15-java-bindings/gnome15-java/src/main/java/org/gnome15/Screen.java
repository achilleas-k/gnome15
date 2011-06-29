package org.gnome15;

import java.util.List;
import org.freedesktop.dbus.DBusInterface;
import org.freedesktop.dbus.DBusSignal;
import org.freedesktop.dbus.UInt32;
import org.freedesktop.dbus.exceptions.DBusException;

public interface Screen extends DBusInterface {
	public static class PageDeleted extends DBusSignal {
		public final String page_path;

		public PageDeleted(String path, String page_path) throws DBusException {
			super(path, page_path);
			this.page_path = page_path;
		}
	}

	public static class MemoryBankChanged extends DBusSignal {
		public final UInt32 new_memory_bank;

		public MemoryBankChanged(String path, UInt32 new_memory_bank) throws DBusException {
			super(path, new_memory_bank);
			this.new_memory_bank = new_memory_bank;
		}
	}

	public static class Connected extends DBusSignal {
		public final String driver_name;

		public Connected(String path, String driver_name) throws DBusException {
			super(path, driver_name);
			this.driver_name = driver_name;
		}
	}

	public static class KeysPressed extends DBusSignal {
		public final List<String> keys;

		public KeysPressed(String path, List<String> keys) throws DBusException {
			super(path, keys);
			this.keys = keys;
		}
	}

	public static class AttentionRequested extends DBusSignal {
		public final String message;

		public AttentionRequested(String path, String message) throws DBusException {
			super(path, message);
			this.message = message;
		}
	}

	public static class Disconnected extends DBusSignal {
		public final String driver_name;

		public Disconnected(String path, String driver_name) throws DBusException {
			super(path, driver_name);
			this.driver_name = driver_name;
		}
	}

	public static class PageTitleChanged extends DBusSignal {
		public final String page_path;
		public final String new_title;

		public PageTitleChanged(String path, String page_path, String new_title) throws DBusException {
			super(path, page_path, new_title);
			this.page_path = page_path;
			this.new_title = new_title;
		}
	}

	public static class PageChanged extends DBusSignal {
		public final String page_path;

		public PageChanged(String path, String page_path) throws DBusException {
			super(path, page_path);
			this.page_path = page_path;
		}
	}

	public static class Action extends DBusSignal {
		public final String binding;

		public Action(String path, String binding) throws DBusException {
			super(path, binding);
			this.binding = binding;
		}
	}

	public static class AttentionCleared extends DBusSignal {
		public AttentionCleared(String path) throws DBusException {
			super(path);
		}
	}

	public static class KeysReleased extends DBusSignal {
		public final List<String> keys;

		public KeysReleased(String path, List<String> keys) throws DBusException {
			super(path, keys);
			this.keys = keys;
		}
	}

	public static class PageCreated extends DBusSignal {
		public final String page_path;
		public final String title;

		public PageCreated(String path, String page_path, String title) throws DBusException {
			super(path, page_path, title);
			this.page_path = page_path;
			this.title = title;
		}
	}

	public static class PageDeleting extends DBusSignal {
		public final String page_path;

		public PageDeleting(String path, String page_path) throws DBusException {
			super(path, page_path);
			this.page_path = page_path;
		}
	}

	public String GetLastError();

	public UInt32 GetVisiblePage(String id);

	public String AcquireControl(String control_id, double release_after, String value);

	public List<String> GetPagesBelowPriority(short priority);

	public void SetReceiveActions(boolean enabled);

	public String GetDeviceUID();

	public boolean IsReceiveActions();

	public boolean IsAttentionRequested();

	public void CycleKeyboard(short value);

	public void ClearAttention();

	public boolean IsConnected();

	public void ReserveKey(String key_name);

	public void Cycle(short cycle);

	public void RequestAttention(String message);

	public void UnreserveKey(String key_name);

	public UInt32 GetPageForID(String id);

	public String GetMessage();

	public String CreatePage(String id, String title, short priority);

	public Quintuple<String, String, Short, Short, Short> GetDriverInformation();

	public List<String> GetControlIds();

	public Quad<String, String, String, String> GetDeviceInformation();

	public void ClearPopup();

	public List<String> GetPages();

}
