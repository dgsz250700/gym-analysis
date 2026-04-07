package Funred;

import java.net.*;
import java.io.*;
public class EnviarArchivo
{

	private String nombreArchivo = "";
	private RecibirArchivo ser;
	private int cwnd = 2;
	private int sst = 16;
	private int cw = 16;
	private int um = 24;

	public EnviarArchivo( String nombreArchivo )
	{
		this.nombreArchivo = nombreArchivo;
	}

	public void enviarArchivo( )
	
	{

		try
		{

			// Creamos la direccion IP de la maquina que recibira el archivo
			InetAddress direccion = InetAddress.getByName( "localHost" );

			// Creamos el Socket con la direccion y elpuerto de comunicacion
			Socket socket = new Socket( direccion, 49400 );
			socket.setSoTimeout( 2000 );
			socket.setKeepAlive( true );

			// Creamos el archivo que vamos a enviar
			File archivo = new File( nombreArchivo );

			// Obtenemos el tamaño del archivo
			int tamañoArchivo = ( int )archivo.length();

			// Creamos el flujo de salida, este tipo de flujo nos permite 
			// hacer la escritura de diferentes tipos de datos tales como
			// Strings, boolean, caracteres y la familia de enteros, etc.
			DataOutputStream dos = new DataOutputStream( socket.getOutputStream() );
			DataInputStream dis = new DataInputStream( socket.getInputStream() );
			System.out.println( "Enviando Archivo: "+archivo.getName() );

			// Enviamos el nombre del archivo 
			dos.writeUTF( archivo.getName() );

			dis.readUTF();
			// Enviamos el tamaño del archivo
			dos.writeInt( tamañoArchivo );

			// Creamos flujo de entrada para realizar la lectura del archivo en bytes
			FileInputStream fis = new FileInputStream( nombreArchivo );
			BufferedInputStream bis = new BufferedInputStream( fis );

			// Creamos el flujo de salida para enviar los datos del archivo en bytes
			BufferedOutputStream bos = new BufferedOutputStream( socket.getOutputStream());

			// Creamos un array de tipo byte con el tamaño del archivo 
			byte[] buffer = new byte[ tamañoArchivo ];

			// Leemos el archivo y lo introducimos en el array de bytes 
			bis.read( buffer ); 

			//Slow-Start

			if(dis.readInt()== 1){
				while(cwnd<sst){
					for(int j=1; j < 4 ; j++){
						cwnd = cwnd^j;
						socket.setSoTimeout(2);
					}
				}

				for( int i = 0; i < cwnd +1 ; i ++){
					bos.write(buffer[ i ]);
				}
			}



			// Congestion Avoidance
			if(cwnd >= sst){
				while(cw < um){
					for( int i = 0; i < cw+1; i ++){
						bos.write(buffer[ i ]);
						socket.setSoTimeout(1+i);
						//Recuperacion Rapida
						if( dis.readInt()== 0  && i == 24){
							bos.write(buffer[ 24 ]);
							sst = cwnd /2;
							while(cwnd<sst){
								for(int j=1; j < 10 ; j++){
									cwnd = cwnd^j;
									socket.setSoTimeout(2);
									if(cwnd >= sst){
										while(cw < 20){
											for( int k = 0; i < cw+1; k ++){
												bos.write(buffer[ k ]);
												socket.setSoTimeout(1+k);
								}
							}
						}

					}

				}
			}

			// Realizamos el envio de los bytes que conforman el archivo
			// i se incrementa, es decir envia cada byte, de acuerdo con el valor de la ventana 



			System.out.println( "Archivo Enviado: "+archivo.getName() );
			// Cerramos socket y flujos
			bis.close();
			bos.close();
			socket.close(); 
	
		catch( Exception e )
		{
			System.out.println( e.toString() );
		}

	}

	// Lanzamos nuestro cliente para realizar el envio del archivo calc.exe
	// ubicado en C:\Windows\calc.exe
	public static void main( String args[] )
	{
		EnviarArchivo ea = new EnviarArchivo( "d:\\Documents\\Arecibir");
		ea.enviarArchivo();
	}
}
