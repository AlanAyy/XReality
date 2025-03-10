// Based on this code: https://gist.github.com/unitycoder/7ad714e72f5fed1c50c6d7a188082388#file-udplistener-cs-L55

using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using NaughtyAttributes;
using UnityEngine;
using UnityEngine.UI;

public class UDPListener : MonoBehaviour
{
    UdpClient clientData;
    int defaultPort = 23232;
    public int receiveBufferSize = 65535;

    public bool showDebug = true;
    IPEndPoint ipEndPointData;
    private object obj = null;
    private System.AsyncCallback AC;
    byte[] receivedBytes;

    private Texture2D receivedTexture;
    public RawImage display;  // Assign this in Unity Inspector
    private bool newFrameAvailable = false;
    private bool resetFrame = false;
    private object frameLock = new object();

    private const string DEFAULT_IP = "255.255.255.255";
    private string crawlerIP = DEFAULT_IP;
    private string localIP = null;
    // private const int TIMEOUT_SECS = 5;  // seconds
    private System.DateTime lastConnectionTime;

    void Start()
    {
        InitializeUDPListener();
        receivedTexture = new Texture2D(640, 480);  // Match Pi Camera resolution
        localIP = GetLocalIPAddress();
        if (showDebug) Debug.Log("Local IP: " + localIP);
    }

    public void InitializeUDPListener()
    {
        InitializeUDPListener(IPAddress.Any);
    }

    public void InitializeUDPListener(IPAddress address)
    {
        ipEndPointData = new IPEndPoint(address, defaultPort);
        clientData = new UdpClient(ipEndPointData);
        clientData.Client.ReceiveBufferSize = receiveBufferSize;
        if (showDebug) Debug.Log("BufSize: " + clientData.Client.ReceiveBufferSize);
        AC = new System.AsyncCallback(ReceivedUDPPacket);
        clientData.BeginReceive(AC, obj);
        if (showDebug) Debug.Log("UDP - Start Receiving...");
    }

    void ReceivedUDPPacket(System.IAsyncResult result)
    {
        receivedBytes = clientData.EndReceive(result, ref ipEndPointData);
        Debug.Log("Received UDP packet from " + ipEndPointData.Address + ":" + ipEndPointData.Port);
        // if (ipEndPointData.Address.ToString() == localIP) return;  // Ignore local packets
        ParsePacket();
        clientData.BeginReceive(AC, obj);
    } // ReceiveCallBack

    public static string GetLocalIPAddress()
    {
        // Source: https://stackoverflow.com/questions/6803073/get-local-ip-address
        var host = Dns.GetHostEntry(Dns.GetHostName());
        foreach (var ip in host.AddressList)
        {
            if (ip.AddressFamily == AddressFamily.InterNetwork) return ip.ToString();
        }
        Debug.LogError("No network adapters with an IPv4 address in the system!");
        return null;
    }

    [Button]
    public void SendTestUDPPacket()
    {
        SendUDPPacket("connect");
        // SendUDPPacket("step 45 45 -75 45 0 -75 45 0 -30 45 45 -75");
        // SendUDPPacket("disconnect");
    }

    public void SendUDPPacket(string message)
    {
        try
        {
            byte[] data = System.Text.Encoding.UTF8.GetBytes(message);
            // TODO: Could optimize here?
            IPEndPoint crawlerEndPoint = new IPEndPoint(IPAddress.Parse(crawlerIP), defaultPort);
            clientData.Send(data, data.Length, crawlerEndPoint);
            if (showDebug) Debug.Log($"Sent UDP Packet to {crawlerEndPoint.Address}:{crawlerEndPoint.Port}");
            // Handle disconnection locally
            if (message == "disconnect") HandleDisconnected();
            // All other commands should be handled by the PiCrawler
        }
        catch (System.Exception e)
        {
            Debug.LogError("Error sending UDP packet: " + e.Message);
        }
    }

    void HandleConnected()
    {
        if (showDebug) Debug.Log("Connected to RealityCrawler!");
        if (crawlerIP != DEFAULT_IP) return;  // Ignore if already connected
        lastConnectionTime = System.DateTime.Now;
        string newIP = ipEndPointData.Address.ToString();
        if (newIP != DEFAULT_IP && newIP != localIP) {
            crawlerIP = newIP;
            if (showDebug) Debug.Log($"Crawler IP set to {crawlerIP}");
            lastConnectionTime = System.DateTime.Now;
        }
    }

    void HandleDisconnected()
    {
        if (showDebug) Debug.Log("Disconnected from RealityCrawler");
        if (crawlerIP == DEFAULT_IP) return;  // Ignore if already disconnected
        crawlerIP = DEFAULT_IP;
        if (showDebug) Debug.Log($"Crawler IP reset to {crawlerIP}");
        resetFrame = true;
    }

    void ParsePacket()
    {
        // TODO: Not really thread safe... Maybe pass the receivedBytes and IP as arguments
        if (showDebug) Debug.Log("receivedBytes length: " + receivedBytes.Length);
        // Handle small messages (commands)
        if (receivedBytes.Length < 1000) {
            string message = System.Text.Encoding.Default.GetString(receivedBytes);
            // Ignore local or foreign packets
            if (ipEndPointData.Address.ToString() == localIP) return;
            else if (crawlerIP != DEFAULT_IP && ipEndPointData.Address.ToString() != crawlerIP) {
                if (showDebug) Debug.Log($"Ignoring packet from unknown IP: {ipEndPointData.Address}");
                return;
            }
            // Handle commands
            if (message == "connected") HandleConnected();
            else if (message == "disconnected") HandleDisconnected();
            if (showDebug) Debug.Log($"Message: {message}");
        }
        // Handle big messages (image frames)
        else {
            lock (frameLock)  // Ensure thread safety
            {
                // if (showDebug) Debug.Log("Image received");
                newFrameAvailable = true;
            }
        }
    }

    void Update()
    {
        // Check if connection is stale (DISABLED FOR NOW)
        // if (crawlerIP != DEFAULT_IP && System.DateTime.Compare(lastConnectionTime.AddSeconds(TIMEOUT_SECS), System.DateTime.Now) < 0) SendUDPPacket("disconnect");
        // Update the display with the new frame
        if (newFrameAvailable)
        {
            lock (frameLock)  // Avoid thread conflicts
            {
                receivedTexture.LoadImage(receivedBytes);  // Decode JPEG
                newFrameAvailable = false;
                // if (showDebug) Debug.Log("Frame loaded");
                display.texture = receivedTexture;  // Apply texture to UI
            }
        }
        if (resetFrame)
        {
            receivedTexture = new Texture2D(640, 480);
            Color32[] whitePixels = new Color32[640 * 480];
            for (int i = 0; i < whitePixels.Length; i++)
            {
                whitePixels[i] = new Color32(255, 255, 255, 255);  // White color
            }
            receivedTexture.SetPixels32(whitePixels);
            receivedTexture.Apply();
            display.texture = receivedTexture;  // Apply texture to UI
            resetFrame = false;
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