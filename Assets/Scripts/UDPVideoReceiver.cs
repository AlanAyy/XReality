using System;
using System.Net;
using System.Net.Sockets;
using UnityEngine;
using UnityEngine.UI;

public class UDPVideoReceiver : MonoBehaviour
{
    public RawImage display;  // Assign this in Unity Inspector
    private UdpClient udpClient;
    private byte[] receivedBytes;
    private Texture2D receivedTexture;
    private bool newFrameAvailable = false;
    private object frameLock = new object();

    void Start()
    {
        udpClient = new UdpClient(23232);  // Listen on this port
        udpClient.BeginReceive(ReceiveData, null);
        receivedTexture = new Texture2D(640, 480, TextureFormat.RGB24, false);  // Match Pi Camera resolution   
    }

    void ReceiveData(IAsyncResult ar)
    {
        IPEndPoint ipEndPoint = new IPEndPoint(IPAddress.Any, 23232);
        byte[] data = udpClient.EndReceive(ar, ref ipEndPoint);
        Debug.Log("Received " + data.Length + " bytes from " + ipEndPoint.Address);

        lock (frameLock)  // Ensure thread safety
        {
            receivedBytes = data;
            newFrameAvailable = true;
        }

        udpClient.BeginReceive(ReceiveData, null);  // Keep receiving
    }

    void Update()
    {
        if (newFrameAvailable)
        {
            lock (frameLock)  // Avoid thread conflicts
            {
                receivedTexture.LoadImage(receivedBytes);  // Decode JPEG
                newFrameAvailable = false;
            }
            Debug.Log("New frame available");
            display.texture = receivedTexture;  // Apply texture to UI
        }
    }

    void OnApplicationQuit()
    {
        udpClient.Close();
    }
}
