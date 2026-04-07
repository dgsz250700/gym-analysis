package Funred;

import java.net.*;
import java.nio.ByteBuffer;
import java.io.*;



class RecibirArchivo
{

	private ServerSocket servidor;
	private int size = 32000; 
	private int ventana = 19900;
	private boolean r = false;
	public RecibirArchivo( ) throws IOException
	{


		// Creamos socket servidor escuchando en el mismo puerto donde se comunica el cliente
		// en este caso el puerto es el 4400
		servidor = new ServerSocket(49400);


		System.out.println( "Esperando recepcion de archivos..." ); 
		System.out.println("Buffer capacity: " + size);
	}

	public void iniciarServidor()
	{
		while( true )
		{

			try
			{
				// Creamos el socket que atendera el servidor
				Socket cliente = servidor.accept(); 

				// Creamos flujo de entrada para leer los datos que envia el cliente 
				DataInputStream dis = new DataInputStream( cliente.getInputStream() );

				// Obtenemos el nombre del archivo
				String nombreArchivo = dis.readUTF().toString(); 
				System.out.println( "Recibiendo archivo "+nombreArchivo );

				// Obtenemos el tamaño del archivo
				int tam = dis.read();



				// Creamos flujo de salida, este flujo nos sirve para 
				// indicar donde guardaremos el archivo
				FileOutputStream fos = new FileOutputStream( "C:\\Users\\user\\Documents\\II Semestre\\Redes\\Arecibir" +nombreArchivo );
				BufferedOutputStream out = new BufferedOutputStream( fos );
				BufferedInputStream in = new BufferedInputStream( cliente.getInputStream() );
				DataOutputStream msj = new DataOutputStream(cliente.getOutputStream());
				// Creamos el array de bytes para leer los datos del archivo

				byte[] buffer = new byte[ tam ];
				ByteBuffer bb = ByteBuffer.allocate(size);


				System.out.println("Buffer remaining bytes: " );

				// Obtenemos el archivo mediante la lectura de bytes enviados
				int ssth = 16;

				if (dis.read()== 24){
					InetAddress direccion = InetAddress.getByName( "localHost" );
					msj.writeInt( 0 );
					msj.writeInt( 0 );
					msj.writeInt( 0 );
					msj.writeUTF("yes");
				}

				int cosa = 0;
				for( int i = 0; i < buffer.length; i++ )
				{

					buffer[ i ] = ( byte )in.read( );
					cosa =+ i;
					int a =+ i;
					ventana =- a;
					msj.writeInt(1);
				}   

				int valor = tam - cosa;

				boolean var = false;

				if(valor > ventana){
					var = true;
				}
				else if(valor >ventana ){
					var = false;
				}
				while (valor > ventana) {
					try{
						cliente.wait();
					}
					catch (InterruptedException e)  {
						Thread.currentThread().interrupt(); 

					}
					var = false;

					notify();
				}

				System.out.println( "Ventana de Recepcion "+ ventana);
				// Escribimos el archivo 
				out.write( buffer ); 

				// Cerramos flujos
				out.flush(); 
				in.close();
				out.close(); 
				cliente.close();

				System.out.println( "Archivo Recibido "+nombreArchivo );

			}
			catch( Exception e )
			{
				System.out.println( "Recibir: "+e.toString() ); 
			}
		} 
		
	}
	


	// Lanzamos el servidor para la recepción de archivos
	public static void main( String args[] ) throws IOException
	{
		System.out.println("aqui estoy");
		new RecibirArchivo().iniciarServidor(); 
	}
}