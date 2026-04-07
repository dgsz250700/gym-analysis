package interfaz;

import java.io.File;
import java.text.Collator;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.TreeSet;

import javax.swing.event.TreeModelEvent;
import javax.swing.event.TreeModelListener;
import javax.swing.filechooser.FileSystemView;
import javax.swing.tree.TreeModel;
import javax.swing.tree.TreePath;


public class FileSystemTreeModel implements TreeModel
{

	private Comparator<File> sortComparator = new Comparator<File>() 
	{
		public int compare(File a, File b)
		{
			Collator collator = Collator.getInstance();
		
			if (a.isDirectory() && b.isFile()) return -1;
			else if (a.isFile() && b.isDirectory()) return +1;
		
			int result = collator.compare(a.getName(), b.getName());
			if (result != 0) return result;
		
			result = collator.compare( a.getAbsolutePath(), b.getAbsolutePath() );
			return result;
		}
	};
	
	private Collection<TreeModelListener> listeners;
	
	private Object falseRoot = new Object();
	
	private File[] roots;
	private FileSystemView fsv;
	
	private boolean hiddenVisible;
	
	private HashMap<File, List<File>> sortedChildren;
	private HashMap<File, Long> lastModifiedTimes;
	

	public FileSystemTreeModel(FileSystemView fsv, File[] roots)
	{
		this.fsv = fsv;
		this.roots = roots;
		
		listeners = new ArrayList<TreeModelListener>();
		sortedChildren = new HashMap<File, List<File>>();
		lastModifiedTimes = new HashMap<File, Long>();
	}
	
	
	public FileSystemTreeModel(FileSystemView fsv)
	{
		this(fsv, fsv.getFiles( FileSystemView.getFileSystemView().getHomeDirectory(), false ) );
	}
	
	
	public FileSystemTreeModel()
	{
		this( FileSystemView.getFileSystemView() );
	}
	
	public Object getRoot()
	{
		return falseRoot;
	}
	
	public Object getChild(Object parent, int index)
	{
		if (parent == falseRoot)
		{
			return roots[index];
		}
		else
		{
			List children = (List) sortedChildren.get(parent);
			return children == null ? null : children.get(index);
		}
	}
	
	public int getChildCount(Object parent)
	{
		if (parent == falseRoot)
		{
			return roots.length;
		}
		else
		{
			File file = (File) parent;
			if (!fsv.isTraversable(file)) return 0;
		
			File[] children = fsv.getFiles(file, !hiddenVisible);
					
			int nChildren = children == null ? 0 : children.length;
		
			long lastModified = file.lastModified();
		
			boolean isFirstTime = lastModifiedTimes.get(file) == null;
			boolean isChanged = false;
		
			if (!isFirstTime)
			{
				Long modified = (Long) lastModifiedTimes.get(file);
				long diff = Math.abs(modified.longValue() - lastModified);
		
				// MS/Win or Samba HACK. Check this!
				isChanged = diff > 4000;
			}
		
			// Sort and register children info
			if (isFirstTime || isChanged)
			{
				lastModifiedTimes.put(file, new Long(lastModified));
			
				TreeSet<File> sorted = new TreeSet<File>(sortComparator);
				for (int i = 0; i < nChildren; i++)
				{									     				     
					 sorted.add(children[i]);
				}
			   
				sortedChildren.put(file, new ArrayList<File>(sorted));
				
			}
			
			// Notify listeners (visual tree typically) if changes
			if (isChanged)
			{
				TreeModelEvent event = new TreeModelEvent(this, getTreePath(file));
				fireTreeStructureChanged(event);
			}
			
			return nChildren;
		}
	}
	
	private Object[] getTreePath(Object obj)
	{
		List<Object> path = new ArrayList<Object>();
		while ( obj != falseRoot )
		{			
			path.add(obj);
			obj = fsv.getParentDirectory((File) obj);
		}
	
		path.add(falseRoot);
	
		int nElements = path.size();
		Object[] treePath = new Object[nElements];
	
		for (int i = 0; i < nElements; i++)
		{
			treePath[i] = path.get(nElements - i - 1);
		}
	
		return treePath;
	}
	
	public boolean isLeaf(Object node)
	{
		if (node == falseRoot) return false;
		else return !fsv.isTraversable((File) node);
	}
	
	public void valueForPathChanged(TreePath path, Object newValue)
	{
	}
	
	public int getIndexOfChild(Object parent, Object child)
	{
		List children = (List) sortedChildren.get(parent);
		return children.indexOf(child);
	}
	
	public void addTreeModelListener(TreeModelListener listener)
	{
	    if (listener != null && !listeners.contains(listener))
	    listeners.add(listener);				
	}
	
	public void removeTreeModelListener(TreeModelListener listener)
	{
		if (listener != null) listeners.remove(listener);
	}
	
	public void fireTreeNodesChanged(TreeModelEvent event)
	{
		for (Iterator i = listeners.iterator(); i.hasNext();)
		{
			TreeModelListener listener = (TreeModelListener) i.next();
			listener.treeNodesChanged(event);
		}
		
	}
	
	public void fireTreeNodesInserted(TreeModelEvent event)
	{
		for (Iterator i = listeners.iterator(); i.hasNext();)
		{
			TreeModelListener listener = (TreeModelListener) i.next();
			listener.treeNodesInserted(event);
		}
	}
	
	public void fireTreeNodesRemoved(TreeModelEvent event)
	{
		for (Iterator i = listeners.iterator(); i.hasNext();)
		{
			TreeModelListener listener = (TreeModelListener) i.next();
			listener.treeNodesRemoved(event);
		}
	}
	
	public void fireTreeStructureChanged(TreeModelEvent event)
	{
		for (Iterator i = listeners.iterator(); i.hasNext();)
		{
			TreeModelListener listener = (TreeModelListener) i.next();
			listener.treeStructureChanged(event);
		}
		
	}
}