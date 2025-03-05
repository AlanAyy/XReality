// Source: https://gist.github.com/unitycoder/7ad714e72f5fed1c50c6d7a188082388#file-udplistener-cs-L55

using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using NaughtyAttributes;
using UnityEngine;

public class UDPListener : MonoBehaviour
{
    UdpClient clientData;
    int portData = 23232;
    public int receiveBufferSize = 120000;

    public bool showDebug = true;
    IPEndPoint ipEndPointData;
    private object obj = null;
    private System.AsyncCallback AC;
    byte[] receivedBytes;

    void Start()
    {
        InitializeUDPListener();
    }

    public void InitializeUDPListener()
    {
        ipEndPointData = new IPEndPoint(IPAddress.Any, portData);
        clientData = new UdpClient();
        clientData.Client.ReceiveBufferSize = receiveBufferSize;
        clientData.Client.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, optionValue: true);
        clientData.ExclusiveAddressUse = false;
        clientData.EnableBroadcast = true;
        clientData.Client.Bind(ipEndPointData);
        clientData.DontFragment = true;
        if (showDebug) Debug.Log("BufSize: " + clientData.Client.ReceiveBufferSize);
        AC = new System.AsyncCallback(ReceivedUDPPacket);
        clientData.BeginReceive(AC, obj);
        Debug.Log("UDP - Start Receiving...");
    }

    void ReceivedUDPPacket(System.IAsyncResult result)
    {
        receivedBytes = clientData.EndReceive(result, ref ipEndPointData);
        ParsePacket();
        clientData.BeginReceive(AC, obj);
    } // ReceiveCallBack

    [Button]
    public void SendTestUDPPacket()
    {
        SendUDPPacket("Test!");
    }

    public void SendUDPPacket(string message)
    {
        try
        {
            byte[] data = System.Text.Encoding.UTF8.GetBytes(message);
            clientData.Send(data, data.Length, new IPEndPoint(IPAddress.Parse("127.0.0.1"), portData));
            if (showDebug) Debug.Log($"Sent UDP Packet to {ipEndPointData.Address}:{ipEndPointData.Port}");
        }
        catch (System.Exception e)
        {
            Debug.LogError("Error sending UDP packet: " + e.Message);
        }
    }

    void ParsePacket()
    {
        // work with receivedBytes
        Debug.Log("receivedBytes len = " + receivedBytes.Length);
        if (receivedBytes.Length < 100)
        {
            Debug.Log("Message: " + System.Text.Encoding.Default.GetString(receivedBytes));
        }
    }

    void OnDestroy()
    {
        if (clientData != null)
        {
            clientData.Close();
        }
    }
}