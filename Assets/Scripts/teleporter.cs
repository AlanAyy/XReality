using UnityEngine;


public class Teleporter : MonoBehaviour
{
    public Transform player;

    // Set these coordinates directly in the Inspector
    public Vector3 cockpitPosition = new Vector3(-11.061f, 0f, 2.195f);
    public Vector3 exitPosition = Vector3.zero;

    // Optional: Set rotation if you want to re-orient the player
    public Vector3 cockpitRotationEuler = Vector3.zero;
    public Vector3 exitRotationEuler = Vector3.zero;

    public void teleportPlayerToCockpit()
    {
        if (player != null)
        {
            player.position = cockpitPosition;
            player.rotation = Quaternion.Euler(cockpitRotationEuler);
        }
        else
        {
            Debug.LogWarning("Player not assigned.");
        }
    }

    public void teleportPlayerOutOfCockpit()
    {
        if (player != null)
        {
            player.position = exitPosition;
            player.rotation = Quaternion.Euler(exitRotationEuler);
        }
        else
        {
            Debug.LogWarning("Player not assigned.");
        }
    }
}
