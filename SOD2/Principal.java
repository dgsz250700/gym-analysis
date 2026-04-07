/*
* Benemerita Universidad Autonoma de Puebla
* Facultad de Ciencias de la Computacion
* Sistemas Operativos Distribuidos
* 
*/

import javax.swing.*;
import java.awt.*;
import javax.swing.border.*;
import javax.swing.event.*;
import java.io.*;
import java.util.*;
import java.awt.event.*;

public class Principal 
{
	static JTextField txtNombre = null;
	static JTextField txtMod = null;
	static JTextField txtTam = null;
	static JTextField txtDir = null;
    static JButton    btnEnviar = null;
    static String ap = "";
    
	public static void main(String args[])
	{
	    JFrame jf = new JFrame( "Sistema de Archivos" );
	    
	    jf.setDefaultCloseOperation( JFrame.EXIT_ON_CLOSE );
	    
	    JPanel panel = new JPanel( new BorderLayout( ) );	    	   
	    
	    FileSystemTreeModel fstm = new FileSystemTreeModel();
	    FileSystemTreeRenderer fstr = new FileSystemTreeRenderer();
	    	    	    
	    JTree arbol = new JTree( fstm );
		arbol.setCellRenderer( fstr );
		arbol.setRootVisible( false );
		arbol.setShowsRootHandles( true );							
	    
	    arbol.addTreeSelectionListener( new TreeSelectionListener()
	    {
	    	public void valueChanged( TreeSelectionEvent e )
	    	{
	    		File f = new File( e.getPath().getLastPathComponent().toString() );
	    		txtNombre.setText( f.getName() );
	    		Date d = new Date( f.lastModified() );
	    		txtMod.setText( d.toString() );
	    		txtTam.setText( Long.toString( f.length() )+" bytes" );
	    		ap = f.getAbsolutePath();
	    		txtDir.setText( ap );
	    	}
	    });
	    
	    JScrollPane jsp = new JScrollPane( arbol );	  	    
	    
	    panel.add( jsp );	    
	    
	    panel.setBorder( new CompoundBorder( BorderFactory.createEmptyBorder( 5, 5, 5, 5 ), BorderFactory.createTitledBorder( "Archivos" ) ) );
	    	    	    
	    JPanel panelP = new JPanel( new BorderLayout() );
	    
	    JPanel panelPP = new JPanel();
	    panelPP.setLayout( new BorderLayout() );
	    
	    panelPP.add( p1(), "North" );
	    panelPP.add( p2(), "Center" );
	    
	    panelP.add( panel, BorderLayout.WEST );
	    panelP.add( panelPP, BorderLayout.EAST );
	    
	    jf.getContentPane().add( panelP );
	    
	    jf.setSize( 515, 400 );	
	    	
	    jf.setLocation( ( Toolkit.getDefaultToolkit().getScreenSize().width - jf.getSize().width ) / 2, ( Toolkit.getDefaultToolkit().getScreenSize().height - jf.getSize().height ) / 2 );
	    
	    jf.setVisible( true );
	} 
    
    public static JPanel p1()
    {
    	JPanel p1 = new JPanel(  );
    	p1.setLayout( new GridLayout( 5, 1 ) );
    	
    	p1.setBorder( new CompoundBorder( BorderFactory.createEmptyBorder( 5, 5, 5, 5 ), BorderFactory.createTitledBorder( " Caracteristicas " ) ) );
    	
    	JPanel panel1 = new JPanel( new GridLayout( 2, 1, 0, 0 ) );
    	
    	txtNombre = new JTextField( 24 );
    	JLabel lblNombre = new JLabel( "<html><font color=blue>Nombre del Archivo:</font></html>" );
    	
    	JPanel panel2 = new JPanel( new GridLayout( 2, 1, 0, 0 ) );
    	
    	txtMod = new JTextField( 24 );
    	JLabel lblMod = new JLabel( "<html><font color=blue>Ultima Modificacion:</font></html>" );
    	
    	JPanel panel3 = new JPanel( new GridLayout( 2, 1, 0, 0 ) );
    	
    	txtTam = new JTextField( 24 );
    	JLabel lblTam = new JLabel( "<html><font color=blue>Tamaño del Archivo:</font></html>" );
    	
    	JPanel panel4 = new JPanel( new GridLayout( 2, 1, 0, 0 ) );
    	
    	txtDir = new JTextField( 24 );
    	JLabel lblDir = new JLabel( "<html><font color=blue>Directorio del Archivo:</font></html>" );
    	    	
    	panel1.add( lblNombre ); panel1.add( txtNombre );
    	panel2.add( lblMod );    panel2.add( txtMod );
    	panel3.add( lblTam );    panel3.add( txtTam );
    	panel4.add( lblDir );    panel4.add( txtDir );
    	
    	p1.add( panel1 );
    	p1.add( panel4 );
    	p1.add( panel2 );
    	p1.add( panel3 );
    	
    	return p1;
    }
    
    public static JPanel p2()
    {
    	
    	JPanel p2 = new JPanel( new FlowLayout( FlowLayout.CENTER ) );
    	
    	p2.setBorder( new CompoundBorder( BorderFactory.createEmptyBorder( 5, 5, 5, 5 ), BorderFactory.createTitledBorder( " Acciones " ) ) );
    	
    	btnEnviar = new JButton( "Enviar" );    	
    	btnEnviar.setSelected( false );
    	
    	btnEnviar.addActionListener( new ActionListener()
    	{
    		public void actionPerformed(ActionEvent ae)
    		{
    			EnviarArchivo ea = new EnviarArchivo( ap );
    			ea.enviarArchivo();    			
    		}
    			
    	});
    	
    	p2.add( btnEnviar );
    	
    	return p2;
    	
    }
    
}