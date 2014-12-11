/* radare - LGPL - Copyright 2009-2014 - pancake */

namespace Radare {
	[Compact]
	[CCode (cheader_filename="r_db.h", cname="RDatabase", free_function="r_db_free", cprefix="r_db_")]
	public class RDatabase {
		/* lifecycle */
		public RDatabase();
		public void free();

		/* storage */
		public int add_id(int off, int size);
		public bool @add(void *b);
		public bool add_unique(void *b);
		public bool delete(void *b);
		public void* get(int key, uint8* buf);

		/* stacky! */
	//	public int push(ref uint8* buf);
	//	public uint8 *pop();
	}
}

namespace SDB {
	[Compact]
	[CCode (name="Sdb", cheader_filename="sdb.h", cname="Sdb", cprefix="sdb_", free_function="sdb_free")]
	public class Sdb {
		/* lifecycle */
		public Sdb (string? path=null, string? file=null, bool locked=false);
		public bool sync ();
		/* query */
		public bool query(string cmd);
		public string querys(string? buf=null, int len=0, string cmd="");
		/* string */
		public bool exists (string key);
		public string @get (string key, out uint? cas=null);
		public bool @add (string key, string val, uint32 cas=0);
		public bool @set (string key, string val, uint32 cas=0);
		/* boolean */
		public bool bool_get (string key, out uint32? cas=null);
		public bool bool_set (string key, bool v, uint32 cas=0);
		/* arrays */
		public int array_length (string key);
		public string array_get (string key, int idx, out uint32 *cas=null);
		public int array_set (string key, int idx, string val, uint32 cas=0);
		public bool array_delete (string key, int idx, uint32 cas=0);
		/* numeric */
		public bool num_exists (string key);
		public bool num_set (string key, uint64 num, uint32 cas=0);
		public uint64 num_get (string key, out uint32 *cas = null);
		public uint64 num_inc (string key, uint64 n, uint32 cas=0);
		public uint64 num_dec (string key, uint64 n, uint32 cas=0);
		/* json */
		public string json_get (string key, string path, out uint32 *cas = null);
		public int json_set (string key, string path, string val, uint32 cas);
//TODO : st64? ut64 here too?
		public int json_num_get (string key, string path, out uint32 *cas = null);
		public int json_num_set (string key, string path, int v, uint32 cas=0);
		public int json_num_inc (string key, string path, int n, uint32 cas=0);
		public int json_num_dec (string key, string path, int n, uint32 cas=0);
		public static string json_indent (string json);
		public static string json_unindent (string json);
		/* remove */
		public bool unset (string key, int cas=0);
		public void reset ();
		public void unlink ();
		/* time */
		public uint64 expire_get (string key, out uint32 *cas = null);
		public bool expire_set (string key, uint64 time, uint32 cas=0);
		public static uint64 now ();
	}
}
